"""IPC de España (INE) y cálculo de rentabilidad real.

La serie utilizada es el índice general nacional del IPC (base 2021), que el
INE publica mensualmente. Se guarda en ``datos/ipc.json`` durante una semana.

La rentabilidad real se calcula con el nivel del índice, no con la tasa
interanual, para que el resultado acumulado sea exacto:

    real = (1 + nominal) / (1 + inflación) - 1
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from ..config import DATOS, HORAS_CACHE_IPC, USER_AGENT

# Índice general nacional. El INE devuelve la serie con la base vigente (2021).
_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/IPC290751?nult=400"
_VERSION_CACHE = 1
_SERIE = "IPC290751"


class ErrorInflacion(Exception):
    """No se han podido obtener los datos del IPC."""


def _ruta_cache():
    return DATOS / "ipc.json"


def _leer_json(ruta):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _escribir_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    temporal.replace(ruta)


def _fresco(ruta, horas=HORAS_CACHE_IPC) -> bool:
    try:
        edad = time.time() - ruta.stat().st_mtime
    except OSError:
        return False
    return edad < horas * 3600


def _descargar() -> dict:
    peticion = urllib.request.Request(
        _URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "es-ES,es;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            texto = respuesta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        raise ErrorInflacion(
            f"La API del INE respondió con un error HTTP {error.code}."
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ErrorInflacion(
            "No se ha podido conectar con la API del INE. Comprueba tu conexión."
        ) from error

    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorInflacion("El INE devolvió una respuesta ilegible.") from error


def _parsear(datos: dict) -> tuple[pd.Series, dict]:
    registros = datos.get("Data") or []
    if not registros:
        raise ErrorInflacion("La respuesta del INE no contiene datos del IPC.")

    valores = {}
    for registro in registros:
        try:
            fecha = pd.Timestamp(
                year=int(registro["Anyo"]),
                month=int(registro["FK_Periodo"]),
                day=1,
            )
            valor = float(registro["Valor"])
        except (KeyError, TypeError, ValueError):
            continue
        valores[fecha] = valor

    if not valores:
        raise ErrorInflacion("No se han podido interpretar los datos del IPC.")

    serie = pd.Series(valores, dtype="float64").sort_index()
    serie = serie[~serie.index.duplicated(keep="last")]

    meta = {
        "fuente": "INE",
        "serie": _SERIE,
        "nombre": datos.get("Nombre") or "IPC general nacional",
        "base": "2021",
        "primer_dato": serie.index[0].strftime("%Y-%m-%d"),
        "ultimo_dato": serie.index[-1].strftime("%Y-%m-%d"),
        "descargado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return serie, meta


def cargar_ipc(sin_cache: bool = False) -> tuple[pd.Series, dict]:
    """Devuelve el índice mensual del IPC y sus metadatos."""
    ruta = _ruta_cache()

    if not sin_cache and _fresco(ruta):
        guardado = _leer_json(ruta)
        if guardado and guardado.get("version") == _VERSION_CACHE:
            try:
                serie = pd.Series(
                    guardado["valores"],
                    index=pd.to_datetime(guardado["fechas"]),
                    dtype="float64",
                )
                return serie, guardado.get("meta", {})
            except (KeyError, ValueError):
                pass

    serie, meta = _parsear(_descargar())
    _escribir_json(
        ruta,
        {
            "version": _VERSION_CACHE,
            "meta": meta,
            "fechas": [fecha.strftime("%Y-%m-%d") for fecha in serie.index],
            "valores": [round(float(valor), 6) for valor in serie.to_numpy()],
        },
    )
    return serie, meta


def nivel(ipc: pd.Series, fecha) -> float | None:
    """Nivel del IPC en el mes de ``fecha`` (último dato disponible)."""
    if ipc is None or ipc.empty:
        return None
    mes = pd.Timestamp(fecha).replace(day=1)
    anteriores = ipc[ipc.index <= mes]
    if anteriores.empty:
        return None
    return float(anteriores.iloc[-1])


def acumulada(ipc: pd.Series, inicio, fin) -> float | None:
    """Inflación acumulada entre dos fechas, en tanto por uno."""
    inicial = nivel(ipc, inicio)
    final = nivel(ipc, fin)
    if inicial is None or final is None or inicial <= 0:
        return None
    return final / inicial - 1


def real(nominal: float | None, inflacion: float | None) -> float | None:
    """Rentabilidad real a partir de la nominal y la inflación."""
    if nominal is None or inflacion is None:
        return None
    return (1 + nominal) / (1 + inflacion) - 1


def anualizar(valor: float | None, dias: float | None) -> float | None:
    """Convierte una rentabilidad acumulada en tasa anual compuesta."""
    if valor is None or not dias or dias <= 0:
        return None
    return (1 + valor) ** (365.25 / dias) - 1
