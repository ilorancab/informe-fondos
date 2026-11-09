"""Aplicación web mínima para generar y servir los informes HTML.

Se apoya en el CLI existente: cada petición lanza ``python -m informe_fondos`` con
los argumentos elegidos en el formulario y sirve el HTML resultante desde
``salida/``. No hay base de datos: los informes son archivos.
"""

from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from ..catalogo import CATALOGO, POPULARES
from ..config import (
    APORTACION_POR_DEFECTO,
    FRECUENCIA_APORTACION_POR_DEFECTO,
    SALIDA,
    valor_env,
)
from ..datos.fuentes import ErrorFuente, buscar_candidatos

HOME = SALIDA.parent
WEB = Path(__file__).resolve().parent
SALIDA.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=WEB / "templates")

PERIODOS = [
    ("1d", "1 día"),
    ("1w", "1 semana"),
    ("5d", "5 días"),
    ("1m", "1 mes"),
    ("3m", "3 meses"),
    ("6m", "6 meses"),
    ("ytd", "Año en curso"),
    ("1a", "1 año"),
    ("2a", "2 años"),
    ("3a", "3 años"),
    ("5a", "5 años"),
    ("7a", "7 años"),
    ("10a", "10 años"),
    ("max", "Todo el histórico"),
]


def _grupos_populares() -> list[dict]:
    """Separa las sugerencias de la portada en fondos y ETFs."""
    return [
        {"titulo": "Fondos indexados", "fondos": CATALOGO},
        {"titulo": "ETFs", "fondos": POPULARES[len(CATALOGO):]},
    ]


# Valores iniciales del formulario, tomados de .env o de los valores por defecto.
APORTA_INICIAL = float(
    valor_env(
        "APORTACION_PERIODICA",
        valor_env("APORTACION_MENSUAL", APORTACION_POR_DEFECTO),
    )
)
FRECUENCIA_INICIAL = valor_env(
    "FRECUENCIA_APORTACION", FRECUENCIA_APORTACION_POR_DEFECTO
)
if FRECUENCIA_INICIAL not in ("mensual", "semanal", "quincenal"):
    FRECUENCIA_INICIAL = "mensual"

TEMA_INICIAL = valor_env("TEMA", "auto")
if TEMA_INICIAL not in ("auto", "claro", "oscuro"):
    TEMA_INICIAL = "auto"

INFLACION_INICIAL = valor_env("INFLACION", "espana")
if INFLACION_INICIAL not in ("espana", "ninguna"):
    INFLACION_INICIAL = "espana"

WEB_USUARIO = os.environ.get("WEB_USUARIO", "").strip()
WEB_CLAVE = os.environ.get("WEB_CLAVE", "").strip()

_RE_IDENTIFICADOR = re.compile(r"^[A-Za-z0-9.^=-]{2,24}$")
_RE_HTML = re.compile(r"^[A-Za-z0-9._-]+\.html$")

_seguridad = HTTPBasic(auto_error=False)
_candado = threading.Lock()

# Caché en memoria de búsquedas para no golpear Yahoo con cada pulsación.
_BUSQUEDA_TTL = 600
_BUSQUEDA_MAX = 200
_cache_busqueda: dict[str, tuple[float, dict]] = {}
_cache_busqueda_lock = threading.Lock()


def verificar_auth(
    credenciales: HTTPBasicCredentials | None = Depends(_seguridad),
) -> None:
    """HTTP Basic opcional: solo se activa si hay usuario y clave."""
    if not WEB_USUARIO or not WEB_CLAVE:
        return
    if credenciales is None or not (
        secrets.compare_digest(credenciales.username, WEB_USUARIO)
        and secrets.compare_digest(credenciales.password, WEB_CLAVE)
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": 'Basic realm="informe-fondos"'},
        )


class Peticion(BaseModel):
    identificadores: str = ""
    catalogo: bool = False
    periodo: Literal[
        "1d", "1w", "5d", "1m", "3m", "6m", "ytd", "1a", "2a", "3a", "5a",
        "7a", "10a", "max",
    ] = "5a"
    aporta: float = Field(default=APORTA_INICIAL, gt=0, le=100000)
    frecuencia_aportacion: Literal["mensual", "semanal", "quincenal"] = (
        FRECUENCIA_INICIAL
    )
    tema: Literal["auto", "claro", "oscuro"] = TEMA_INICIAL
    inflacion: Literal["espana", "ninguna"] = INFLACION_INICIAL
    benchmark: str = ""
    sin_benchmark: bool = False
    posiciones: bool = False
    cdn: bool = True


def _limpiar_identificadores(texto: str) -> list[str]:
    partes = [parte for parte in re.split(r"[\s,;]+", texto.strip()) if parte]
    if len(partes) > 10:
        raise HTTPException(400, "Máximo 10 identificadores por informe.")
    for parte in partes:
        if not _RE_IDENTIFICADOR.match(parte):
            raise HTTPException(
                400, f"Identificador no válido: «{parte}». Usa un ISIN o un ticker."
            )
    return partes


def _slug(texto: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "-", texto).strip("-").lower()
    return (limpio[:50] or "fondo").strip("-")


def _ruta_informe(nombre: str) -> Path:
    if not _RE_HTML.match(nombre):
        raise HTTPException(404, "Informe no encontrado.")
    ruta = (SALIDA / nombre).resolve()
    if ruta.parent != SALIDA.resolve() or not ruta.is_file():
        raise HTTPException(404, "Informe no encontrado.")
    return ruta


def _listar_informes() -> list[dict]:
    SALIDA.mkdir(parents=True, exist_ok=True)
    rutas = sorted(
        SALIDA.glob("*.html"),
        key=lambda ruta: ruta.stat().st_mtime,
        reverse=True,
    )[:50]
    informes = []
    for ruta in rutas:
        try:
            datos = ruta.stat()
        except OSError:
            continue
        informes.append(
            {
                "nombre": ruta.name,
                "url": f"/informes/{quote(ruta.name)}",
                "fecha": datetime.fromtimestamp(datos.st_mtime).strftime(
                    "%d/%m/%Y %H:%M"
                ),
                "kb": datos.st_size / 1024,
            }
        )
    return informes


def _ultimo_informe() -> str | None:
    informes = _listar_informes()
    return informes[0]["nombre"] if informes else None


app = FastAPI(
    title="Informe de fondos",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/salud")
def salud():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, _: None = Depends(verificar_auth)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "informes": _listar_informes(),
            "periodos": PERIODOS,
            "grupos_populares": _grupos_populares(),
            "aporta": APORTA_INICIAL,
            "frecuencia": FRECUENCIA_INICIAL,
            "tema": TEMA_INICIAL,
            "inflacion": INFLACION_INICIAL,
        },
    )


@app.get("/api/buscar")
def api_buscar(q: str = "", _: None = Depends(verificar_auth)):
    consulta = q.strip()
    if len(consulta) < 2:
        return {"resultados": [], "mensaje": "Escribe al menos 2 caracteres."}

    clave = consulta.casefold()
    ahora = time.monotonic()
    with _cache_busqueda_lock:
        guardado = _cache_busqueda.get(clave)
        if guardado and ahora - guardado[0] < _BUSQUEDA_TTL:
            return guardado[1]

    try:
        resultados = buscar_candidatos(consulta)
        mensaje = (
            ""
            if resultados
            else "Sin resultados. Prueba con otro nombre, ISIN o ticker."
        )
    except ErrorFuente as error:
        resultados = []
        mensaje = str(error)

    respuesta = {"resultados": resultados, "mensaje": mensaje}
    with _cache_busqueda_lock:
        if len(_cache_busqueda) >= _BUSQUEDA_MAX:
            # Se descarta la entrada más antigua para acotar la memoria.
            mas_antigua = min(_cache_busqueda, key=lambda k: _cache_busqueda[k][0])
            _cache_busqueda.pop(mas_antigua, None)
        _cache_busqueda[clave] = (ahora, respuesta)
    return respuesta


@app.get("/api/informes")
def api_informes(_: None = Depends(verificar_auth)):
    return {"informes": _listar_informes()}


@app.get("/ultimo")
def ver_ultimo(_: None = Depends(verificar_auth)):
    nombre = _ultimo_informe()
    if not nombre:
        raise HTTPException(404, "Todavía no hay informes generados.")
    return RedirectResponse(url=f"/informes/{quote(nombre)}")


@app.post("/api/generar")
def generar(peticion: Peticion, _: None = Depends(verificar_auth)):
    identificadores = _limpiar_identificadores(peticion.identificadores)
    if not peticion.catalogo and not identificadores:
        raise HTTPException(
            400, "Indica al menos un ISIN o marca «Usar catálogo completo»."
        )

    benchmark = peticion.benchmark.strip().upper()
    if benchmark and not _RE_IDENTIFICADOR.match(benchmark):
        raise HTTPException(400, f"Símbolo de referencia no válido: «{benchmark}».")

    if not _candado.acquire(blocking=False):
        raise HTTPException(
            409,
            "Ya se está generando otro informe. Espera a que termine e inténtalo de nuevo.",
        )

    try:
        SALIDA.mkdir(parents=True, exist_ok=True)
        base = "catalogo" if peticion.catalogo else "-".join(identificadores)
        nombre = (
            f"web-{datetime.now():%Y%m%d-%H%M%S}-{_slug(base)}-"
            f"{uuid4().hex[:6]}.html"
        )
        ruta = SALIDA / nombre

        comando = [sys.executable, "-m", "informe_fondos"]
        if peticion.catalogo:
            comando.append("--catalogo")
        else:
            comando.extend(identificadores)
        comando.extend(
            [
                "--periodo",
                peticion.periodo,
                "--aporta",
                str(peticion.aporta),
                "--frecuencia-aportacion",
                peticion.frecuencia_aportacion,
                "--tema",
                peticion.tema,
                "--inflacion",
                peticion.inflacion,
                "--salida",
                str(ruta),
            ]
        )
        if peticion.cdn:
            comando.append("--cdn")
        if peticion.posiciones:
            comando.append("--posiciones")
        if peticion.sin_benchmark:
            comando.append("--sin-benchmark")
        elif benchmark:
            comando.extend(["--benchmark", benchmark])

        try:
            proceso = subprocess.run(
                comando,
                cwd=HOME,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired as error:
            ruta.unlink(missing_ok=True)
            raise HTTPException(
                504, "La generación tardó más de 5 minutos. Inténtalo de nuevo."
            ) from error
        except OSError as error:
            ruta.unlink(missing_ok=True)
            raise HTTPException(
                500, f"No se ha podido ejecutar el generador: {error}"
            ) from error

        log = ((proceso.stdout or "") + (proceso.stderr or "")).strip()
        if proceso.returncode != 0 or not ruta.is_file():
            ruta.unlink(missing_ok=True)
            raise HTTPException(
                502,
                detail={
                    "mensaje": "No se ha podido generar el informe.",
                    "log": log[-4000:],
                },
            )

        return {
            "ok": True,
            "nombre": nombre,
            "url": f"/informes/{quote(nombre)}",
            "log": log[-4000:],
        }
    finally:
        _candado.release()


@app.get("/informes/{nombre}")
def ver_informe(
    nombre: str, descargar: bool = False, _: None = Depends(verificar_auth)
):
    ruta = _ruta_informe(nombre)
    if descargar:
        return FileResponse(ruta, media_type="text/html", filename=nombre)
    return FileResponse(
        ruta,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@app.delete("/api/informes/{nombre}")
def borrar_informe(nombre: str, _: None = Depends(verificar_auth)):
    ruta = _ruta_informe(nombre)
    try:
        ruta.unlink()
    except OSError as error:
        raise HTTPException(500, f"No se ha podido borrar: {error}") from error
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("informe_fondos.web.app:app", host="127.0.0.1", port=8000, reload=True)
