"""Acceso a datos públicos de Yahoo Finance.

Yahoo Finance tiene una API JSON no documentada, pero estable y sin clave,
que permite:

1. Resolver un identificador (ISIN o ticker) a un símbolo de Yahoo.
2. Descargar la serie histórica de precios o valores liquidativos.

Este módulo encapsula esas dos operaciones, añade caché en disco y traduce
los errores técnicos a mensajes entendibles.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import pandas as pd

from ..config import DATOS, HORAS_CACHE, SERIES, USER_AGENT, VERSION_CACHE

_BUSQUEDA = "https://query2.finance.yahoo.com/v1/finance/search"
_GRAFICO = "https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"

_RE_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Mercados por los que Yahoo lista fondos europeos. Se usan para desempatar
# cuando un ISIN aparece en varias bolsas.
_MERCADOS_PREFERIDOS = [
    "FRA",  # Frankfurt (fondos .F)
    "GER",  # Xetra
    "LSE",  # Londres
    "AMS",  # Ámsterdam
    "PAR",  # París
    "MIL",  # Milán
    "MCE",  # Madrid
    "STU",  # Stuttgart
    "PNK",  # OTC (fondos .F de EE. UU.)
    "NMS",
    "NYQ",
]


class ErrorFuente(Exception):
    """No se han podido obtener los datos de un instrumento."""


@dataclass(frozen=True)
class Instrumento:
    """Datos identificativos de un fondo o ETF."""

    consulta: str          # lo que escribió el usuario
    simbolo: str           # símbolo de Yahoo Finance
    nombre: str
    divisa: str
    mercado: str
    tipo: str              # MUTUALFUND, ETF, INDEX...
    isin: str | None = None

    @property
    def etiqueta(self) -> str:
        return self.isin or self.simbolo


# --------------------------------------------------------------------------
# Utilidades HTTP y de caché
# --------------------------------------------------------------------------

def es_isin(texto: str) -> bool:
    """Devuelve True si el texto tiene forma de ISIN."""
    return bool(_RE_ISIN.match(texto.strip().upper()))


def _get_json(url: str, timeout: int = 25, intentos: int = 4) -> dict:
    """GET con reintentos y rotación entre los dos hosts de Yahoo."""
    ultimo_error = None
    esperas = [2, 5, 10]

    for intento in range(intentos):
        direccion = url
        if intento % 2 == 1:
            # query1 y query2 sirven lo mismo; alternar ayuda con los límites.
            if "query1.finance.yahoo.com" in direccion:
                direccion = direccion.replace("query1.", "query2.")
            elif "query2.finance.yahoo.com" in direccion:
                direccion = direccion.replace("query2.", "query1.")

        peticion = urllib.request.Request(
            direccion,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            ultimo_error = error
            if error.code in (429, 500, 502, 503, 504) and intento < intentos - 1:
                time.sleep(esperas[min(intento, len(esperas) - 1)])
                continue
            if error.code == 404:
                raise ErrorFuente(
                    "Yahoo Finance no encuentra ese símbolo. Revisa que el ISIN o "
                    "el ticker estén bien escritos."
                ) from error
            if error.code == 429:
                raise ErrorFuente(
                    "Yahoo Finance está limitando las peticiones (error 429). "
                    "Espera 10-15 minutos y vuelve a intentarlo. La caché de 6 "
                    "horas evita repetir descargas ya hechas."
                ) from error
            raise ErrorFuente(
                f"Yahoo Finance respondió con un error HTTP {error.code}."
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            ultimo_error = error
            if intento < intentos - 1:
                time.sleep(esperas[min(intento, len(esperas) - 1)])
                continue
            raise ErrorFuente(
                "No se ha podido conectar con Yahoo Finance. Comprueba tu conexión "
                "a internet e inténtalo de nuevo."
            ) from error
        except json.JSONDecodeError as error:
            raise ErrorFuente("Yahoo Finance devolvió una respuesta ilegible.") from error

    raise ErrorFuente(f"No se ha podido completar la petición: {ultimo_error}")


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


def _fresco(ruta, horas=HORAS_CACHE) -> bool:
    try:
        edad = time.time() - ruta.stat().st_mtime
    except OSError:
        return False
    return edad < horas * 3600


def _archivo_cache(simbolo: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", simbolo)


# --------------------------------------------------------------------------
# Resolución de ISIN / ticker -> símbolo de Yahoo
# --------------------------------------------------------------------------

def _buscar_candidatos(consulta: str, rapido: bool = False) -> list[dict]:
    parametros = urllib.parse.urlencode(
        {
            "q": consulta,
            "quotesCount": 12,
            "newsCount": 0,
            "enableFuzzyQuery": "false",
        }
    )
    if rapido:
        datos = _get_json(f"{_BUSQUEDA}?{parametros}", timeout=6, intentos=1)
    else:
        datos = _get_json(f"{_BUSQUEDA}?{parametros}")
    return datos.get("quotes") or []


def buscar_candidatos(consulta: str, limite: int = 8) -> list[dict]:
    """Busca fondos y ETFs por nombre, ISIN o ticker para el buscador web.

    Devuelve una lista de diccionarios sencillos, ya filtrada y ordenada, sin
    descargar metadatos adicionales. Usa un modo rápido (un solo intento y
    timeout corto) para no bloquear la interfaz si Yahoo va lento.
    """
    consulta = consulta.strip()
    if len(consulta) < 2:
        return []

    candidatos = _buscar_candidatos(consulta, rapido=True)
    resultados = []
    for candidato in sorted(candidatos, key=_puntuar, reverse=True):
        tipo = (candidato.get("quoteType") or "").upper()
        if tipo not in ("ETF", "MUTUALFUND"):
            continue
        simbolo = candidato.get("symbol")
        if not simbolo:
            continue
        nombre = (
            candidato.get("longname")
            or candidato.get("shortname")
            or candidato.get("longName")
            or candidato.get("shortName")
            or simbolo
        )
        resultados.append(
            {
                "simbolo": simbolo,
                "nombre": nombre,
                "isin": consulta.upper() if es_isin(consulta) else None,
                "mercado": candidato.get("exchDisp") or candidato.get("exchange") or "",
                "tipo": "Fondo" if tipo == "MUTUALFUND" else "ETF",
            }
        )
        if len(resultados) >= limite:
            break
    return resultados


def _puntuar(candidato: dict) -> int:
    """Ordena los resultados: fondo antes que ETF y mercados conocidos primero."""
    puntos = 0
    tipo = (candidato.get("quoteType") or "").upper()
    if tipo == "MUTUALFUND":
        puntos += 100
    elif tipo == "ETF":
        puntos += 80
    elif tipo == "INDEX":
        puntos += 40

    mercado = (candidato.get("exchange") or "").upper()
    if mercado in _MERCADOS_PREFERIDOS:
        puntos += 20 - _MERCADOS_PREFERIDOS.index(mercado)

    if (candidato.get("symbol") or "").endswith(".F"):
        puntos += 5

    return puntos


def _meta_rapida(simbolo: str) -> dict:
    """Descarga un año de datos solo para conocer nombre, divisa y mercado."""
    parametros = urllib.parse.urlencode(
        {"range": "1y", "interval": "1d", "includeAdjustedClose": "true"}
    )
    url = _GRAFICO.format(simbolo=urllib.parse.quote(simbolo, safe="")) + "?" + parametros
    datos = _get_json(url)
    resultados = (datos.get("chart") or {}).get("result") or []
    if not resultados:
        raise ErrorFuente(f"Yahoo Finance no devuelve datos para {simbolo}.")
    resultado = resultados[0]
    # Algunos tickers existen en la búsqueda pero no tienen histórico (por
    # ejemplo, ciertas clases cotizadas en Stuttgart). Se descartan aquí para
    # no elegirlos y fallar después al descargar la serie completa.
    if not resultado.get("timestamp"):
        raise ErrorFuente(f"Yahoo Finance no tiene histórico para {simbolo}.")
    return resultado.get("meta") or {}


def resolver(identificador: str, sin_cache: bool = False) -> Instrumento:
    """Convierte un ISIN o un ticker en un :class:`Instrumento` con metadatos."""
    consulta = identificador.strip()
    if not consulta:
        raise ErrorFuente("El identificador está vacío.")

    es_codigo_isin = es_isin(consulta)
    clave = consulta.upper()

    cache_simbolos = DATOS / "simbolos.json"
    cache = _leer_json(cache_simbolos) or {}
    if not sin_cache and clave in cache:
        guardado = cache[clave]
        return Instrumento(
            consulta=consulta,
            simbolo=guardado["simbolo"],
            nombre=guardado["nombre"],
            divisa=guardado["divisa"],
            mercado=guardado["mercado"],
            tipo=guardado["tipo"],
            isin=guardado.get("isin"),
        )

    if es_codigo_isin:
        candidatos = sorted(_buscar_candidatos(consulta), key=_puntuar, reverse=True)
        if not candidatos:
            raise ErrorFuente(
                f"No he encontrado el ISIN {consulta} en Yahoo Finance.\n"
                "Prueba a buscar el fondo en su ficha de Morningstar y usa el "
                "ticker como alternativa (por ejemplo, 0P00000RQC.F)."
            )
        simbolos = [c.get("symbol") for c in candidatos if c.get("symbol")]
    else:
        simbolos = [consulta]

    errores = []
    for simbolo in simbolos[:6]:
        try:
            meta = _meta_rapida(simbolo)
        except ErrorFuente as error:
            errores.append(f"{simbolo}: {error}")
            continue

        nombre = meta.get("longName") or meta.get("shortName") or simbolo
        instrumento = Instrumento(
            consulta=consulta,
            simbolo=simbolo,
            nombre=nombre,
            divisa=meta.get("currency") or "—",
            mercado=meta.get("fullExchangeName") or meta.get("exchangeName") or "—",
            tipo=meta.get("instrumentType") or "—",
            isin=consulta.upper() if es_codigo_isin else None,
        )
        cache[clave] = asdict(instrumento)
        _escribir_json(cache_simbolos, cache)
        return instrumento

    detalle = "\n".join(errores) if errores else "sin detalles"
    raise ErrorFuente(
        f"No he podido obtener datos para {consulta}.\n{detalle}"
    )


# --------------------------------------------------------------------------
# Descarga de la serie histórica
# --------------------------------------------------------------------------

def _parsear_serie(resultado: dict) -> tuple[pd.Series, dict]:
    meta = resultado.get("meta") or {}
    marcas = resultado.get("timestamp") or []
    if not marcas:
        raise ErrorFuente("La respuesta no contiene datos históricos.")

    indicadores = resultado.get("indicators") or {}
    ajustados = ((indicadores.get("adjclose") or [{}])[0] or {}).get("adjclose")
    cierres = ((indicadores.get("quote") or [{}])[0] or {}).get("close")

    # Se prefiere el precio ajustado (incluye dividendos) cuando existe.
    valores = ajustados if ajustados and any(v is not None for v in ajustados) else cierres
    if not valores:
        raise ErrorFuente("La respuesta no contiene precios.")

    zona = meta.get("exchangeTimezoneName") or "UTC"
    fechas = pd.to_datetime(marcas, unit="s", utc=True)
    try:
        fechas = fechas.tz_convert(zona)
    except (KeyError, ValueError):
        pass
    fechas = fechas.tz_localize(None).normalize()

    serie = pd.Series(valores, index=fechas, dtype="float64", name=meta.get("symbol"))
    serie = serie.dropna().sort_index()
    serie = serie[~serie.index.duplicated(keep="last")]

    if serie.empty:
        raise ErrorFuente("La serie histórica está vacía.")

    datos_meta = {
        "simbolo": meta.get("symbol"),
        "nombre": meta.get("longName") or meta.get("shortName"),
        "divisa": meta.get("currency") or "—",
        "mercado": meta.get("fullExchangeName") or meta.get("exchangeName") or "—",
        "tipo": meta.get("instrumentType") or "—",
        "zona": zona,
        "primer_dato": serie.index[0].strftime("%Y-%m-%d"),
        "ultimo_dato": serie.index[-1].strftime("%Y-%m-%d"),
        "descargado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return serie, datos_meta


def descargar(simbolo: str, sin_cache: bool = False) -> tuple[pd.Series, dict]:
    """Descarga (o lee de caché) la serie histórica completa de un símbolo."""
    ruta = SERIES / f"{_archivo_cache(simbolo)}.json"

    if not sin_cache and _fresco(ruta):
        guardado = _leer_json(ruta)
        if guardado and guardado.get("version") == VERSION_CACHE:
            try:
                serie = pd.Series(
                    guardado["valores"],
                    index=pd.to_datetime(guardado["fechas"]),
                    dtype="float64",
                    name=simbolo,
                )
                return serie, guardado.get("meta", {})
            except (KeyError, ValueError):
                # Caché antigua o corrupta: se ignora y se vuelve a descargar.
                pass

    # Se piden fechas explícitas en vez de range=max: con range=max Yahoo
    # devuelve la serie agregada (semanal o mensual) aunque se pida 1d, y eso
    # falsea la volatilidad, los meses y la alineación con el índice.
    parametros = urllib.parse.urlencode(
        {
            "period1": 0,
            "period2": int(time.time()),
            "interval": "1d",
            "includeAdjustedClose": "true",
            "events": "div,splits",
        }
    )
    url = _GRAFICO.format(simbolo=urllib.parse.quote(simbolo, safe="")) + "?" + parametros
    datos = _get_json(url)

    resultados = (datos.get("chart") or {}).get("result") or []
    if not resultados:
        error = (datos.get("chart") or {}).get("error") or {}
        descripcion = error.get("description") or "sin datos"
        raise ErrorFuente(f"Yahoo Finance no devuelve histórico para {simbolo}: {descripcion}")

    serie, meta = _parsear_serie(resultados[0])

    _escribir_json(
        ruta,
        {
            "version": VERSION_CACHE,
            "meta": meta,
            "fechas": [fecha.strftime("%Y-%m-%d") for fecha in serie.index],
            "valores": [round(float(valor), 6) for valor in serie.to_numpy()],
        },
    )
    return serie, meta
