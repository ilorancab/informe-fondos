#!/usr/bin/env python3
"""Genera un informe HTML del estado y la evolución de un fondo indexado.

Ejemplos:
    informe-fondos IE00B03HCZ61
    informe-fondos IE00B03HCZ61 --periodo 5a --aporta 200
    informe-fondos IE00B03HCZ61 IE0032620787 --benchmark IWDA.AS
    informe-fondos --catalogo
    informe-fondos --listar
    informe-fondos IWDA.AS --sin-benchmark --abrir
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .catalogo import CATALOGO
from .config import (
    APORTACION_POR_DEFECTO,
    BENCHMARK_POR_DEFECTO,
    FRECUENCIA_APORTACION_POR_DEFECTO,
    TASA_LIBRE_RIESGO_POR_DEFECTO,
    TEMA_POR_DEFECTO,
    valor_env,
)
from .datos import fuentes, inflacion
from .presentacion import informe
from .presentacion.formato import numero, porcentaje

PERIODOS_VALIDOS = [
    "1d", "1w", "5d", "1m", "3m", "6m", "ytd", "1a", "2a", "3a", "5a", "7a",
    "10a", "max",
]


# --------------------------------------------------------------------------
# Salida por terminal
# --------------------------------------------------------------------------

def _con_color(texto: str, codigo: str) -> str:
    return f"\033[{codigo}m{texto}\033[0m" if sys.stdout.isatty() else texto


def _verde(texto: str) -> str:
    return _con_color(texto, "32")


def _rojo(texto: str) -> str:
    return _con_color(texto, "31")


def _tenue(texto: str) -> str:
    return _con_color(texto, "2")


def _resumen_ficha(ficha: dict) -> None:
    por_codigo = {fila["codigo"]: fila for fila in ficha["rentabilidades"]}

    def valor(codigo):
        return por_codigo[codigo]["rentabilidad"]

    print(f"\n{_con_color(ficha['nombre'], '1')}")
    print(
        _tenue(
            f"  {ficha['isin'] or ficha['simbolo']} · {ficha['simbolo']} · "
            f"{ficha['divisa']} · {ficha['mercado']} · {ficha['num_datos']} datos "
            f"{ficha.get('frecuencia_plural') or ''} "
            f"({ficha['fecha_inicio']:%d/%m/%Y} → {ficha['fecha_datos']:%d/%m/%Y})"
        )
    )
    print(f"  Último valor: {ficha['kpis'][0]['valor']}")
    print(
        "  "
        f"YTD {porcentaje(valor('ytd'))}   "
        f"1a {porcentaje(valor('1a'))}   "
        f"3a anual {porcentaje(por_codigo['3a']['anualizada'])}   "
        f"5a anual {porcentaje(por_codigo['5a']['anualizada'])}"
    )
    print(
        "  "
        f"Volatilidad 3a {porcentaje(ficha['metricas'].get('vol_3a'), signo=False)}   "
        f"Máx. caída {porcentaje(ficha.get('max_caida'))}   "
        f"Sharpe 3a {numero(ficha['metricas'].get('sharpe_3a'), 2)}"
    )


def _listar_catalogo() -> None:
    print("\nFondos indexados de referencia:\n")
    for fondo in CATALOGO:
        print(f"  {_con_color(fondo['isin'], '1')}  {fondo['nombre']}")
        print(_tenue(f"             {fondo['indice']} · {fondo['gestora']} · {fondo['nota']}"))
    print(
        _tenue(
            "\nUsa cualquiera de estos ISIN como argumento, o pasa tu propio "
            "ISIN o ticker.\n"
        )
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="informe-fondos",
        description=(
            "Genera un informe HTML con la evolución, las rentabilidades y el "
            "riesgo de un fondo indexado o ETF."
        ),
        epilog=(
            "Ejemplos:\n"
            "  informe-fondos IE00B03HCZ61\n"
            "  informe-fondos IE00B03HCZ61 --periodo 5a --aporta 300\n"
            "  informe-fondos --catalogo\n"
            "  informe-fondos IE00B03HCZ61 IE0032620787 --abrir\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "identificadores",
        nargs="*",
        metavar="ISIN|TICKER",
        help="ISIN (recomendado) o ticker de Yahoo Finance. Admite varios.",
    )
    parser.add_argument(
        "--catalogo",
        action="store_true",
        help="Genera el informe con todos los fondos del catálogo.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Muestra el catálogo de fondos y termina.",
    )
    parser.add_argument(
        "--periodo",
        default="5a",
        choices=PERIODOS_VALIDOS,
        help="Periodo de los gráficos y del simulador (por defecto: 5a).",
    )
    parser.add_argument(
        "--posiciones",
        action="store_true",
        help=(
            "Analiza las 10 mayores posiciones del fondo y su rentabilidad. "
            "Añade varias peticiones a Yahoo y no está disponible en todos "
            "los fondos."
        ),
    )
    parser.add_argument(
        "--benchmark",
        default=None,
        help=(
            "Símbolo del índice de referencia (por defecto: "
            f"{valor_env('BENCHMARK', BENCHMARK_POR_DEFECTO)})."
        ),
    )
    parser.add_argument(
        "--sin-benchmark",
        action="store_true",
        help="No compara con ningún índice.",
    )
    parser.add_argument(
        "--aporta",
        type=float,
        default=float(
            valor_env(
                "APORTACION_PERIODICA",
                valor_env("APORTACION_MENSUAL", APORTACION_POR_DEFECTO),
            )
        ),
        help="Aportación periódica del simulador, en la divisa del fondo.",
    )
    parser.add_argument(
        "--frecuencia-aportacion",
        default=valor_env(
            "FRECUENCIA_APORTACION", FRECUENCIA_APORTACION_POR_DEFECTO
        ),
        choices=["mensual", "semanal", "quincenal"],
        help=(
            "Cada cuánto se hace la aportación del simulador (por defecto: "
            f"{valor_env('FRECUENCIA_APORTACION', FRECUENCIA_APORTACION_POR_DEFECTO)})."
        ),
    )
    parser.add_argument(
        "--tasa-libre-riesgo",
        type=float,
        default=float(valor_env("TASA_LIBRE_RIESGO", TASA_LIBRE_RIESGO_POR_DEFECTO)),
        help="Tasa libre de riesgo anual (%%) para el Sharpe (por defecto: 2).",
    )
    parser.add_argument(
        "--inflacion",
        choices=["espana", "ninguna"],
        default=valor_env("INFLACION", "espana"),
        help=(
            "Añade la rentabilidad real descontando el IPC de España (por defecto: "
            "espana). Usa 'ninguna' para desactivarlo."
        ),
    )
    parser.add_argument(
        "--sin-inflacion",
        action="store_const",
        const="ninguna",
        dest="inflacion",
        default=argparse.SUPPRESS,
        help="Equivale a --inflacion ninguna.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Ruta del HTML de salida.",
    )
    parser.add_argument(
        "--simbolo",
        default=None,
        help="Fuerza un símbolo de Yahoo (útil si un ISIN es ambiguo).",
    )
    parser.add_argument(
        "--sin-cache",
        action="store_true",
        help="Ignora la caché y vuelve a descargar los datos.",
    )
    parser.add_argument(
        "--cdn",
        action="store_true",
        help="Carga Plotly desde internet en vez de incrustarlo (HTML mucho más ligero).",
    )
    parser.add_argument(
        "--tema",
        choices=["auto", "claro", "oscuro"],
        default=valor_env("TEMA", TEMA_POR_DEFECTO),
        help=(
            "Tema visual del informe (por defecto: auto). 'auto' sigue el tema "
            "del sistema; el informe también incluye un botón para cambiarlo."
        ),
    )
    parser.add_argument(
        "--abrir",
        action="store_true",
        help="Abre el informe en el navegador al terminar.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _argumentos(argv)

    if args.listar:
        _listar_catalogo()
        return 0

    if args.catalogo:
        identificadores = [fondo["isin"] for fondo in CATALOGO]
    else:
        identificadores = list(args.identificadores)

    if not identificadores:
        print(
            "Indica al menos un ISIN o ticker. Ejemplo:\n"
            "  informe-fondos IE00B03HCZ61\n\n"
            "Usa --listar para ver el catálogo de fondos de referencia.",
            file=sys.stderr,
        )
        return 2

    if args.simbolo and len(identificadores) > 1:
        print("--simbolo solo se puede usar con un único identificador.", file=sys.stderr)
        return 2

    # 1. Resolver instrumentos
    instrumentos = []
    for identificador in identificadores:
        if args.simbolo:
            identificador = args.simbolo
        try:
            instrumento = fuentes.resolver(identificador, sin_cache=args.sin_cache)
        except fuentes.ErrorFuente as error:
            print(f"⚠️  {identificador}: {error}", file=sys.stderr)
            continue
        instrumentos.append(instrumento)

    if not instrumentos:
        print("No se ha podido resolver ningún instrumento.", file=sys.stderr)
        return 1

    # 2. Descargar series
    series = []
    fichas_base = []
    for instrumento in instrumentos:
        try:
            serie, meta = fuentes.descargar(
                instrumento.simbolo, sin_cache=args.sin_cache
            )
        except fuentes.ErrorFuente as error:
            # La caché de símbolos puede apuntar a una cotización sin histórico
            # (Yahoo lista a veces la misma clase en varios mercados). Se vuelve
            # a resolver una vez, ignorando la caché, antes de rendirse.
            if not args.sin_cache:
                try:
                    nuevo = fuentes.resolver(instrumento.consulta, sin_cache=True)
                    serie, meta = fuentes.descargar(nuevo.simbolo, sin_cache=True)
                    print(
                        f"↻  {instrumento.consulta}: se usa {nuevo.simbolo} "
                        "en lugar del símbolo guardado.",
                        file=sys.stderr,
                    )
                    instrumento = nuevo
                except fuentes.ErrorFuente:
                    print(f"⚠️  {instrumento.nombre}: {error}", file=sys.stderr)
                    continue
            else:
                print(f"⚠️  {instrumento.nombre}: {error}", file=sys.stderr)
                continue
        series.append(serie)
        fichas_base.append((instrumento, serie))

    if not series:
        print("No se ha podido descargar ninguna serie histórica.", file=sys.stderr)
        return 1

    # 3. Índice de referencia
    benchmark_serie = None
    benchmark_nombre = None
    benchmark_divisa = None
    if not args.sin_benchmark:
        simbolo_benchmark = args.benchmark or valor_env("BENCHMARK", BENCHMARK_POR_DEFECTO)
        try:
            referencia = fuentes.resolver(simbolo_benchmark, sin_cache=args.sin_cache)
            benchmark_serie, _ = fuentes.descargar(
                referencia.simbolo, sin_cache=args.sin_cache
            )
            benchmark_nombre = referencia.nombre
            benchmark_divisa = referencia.divisa
        except fuentes.ErrorFuente as error:
            print(
                f"⚠️  No se ha podido cargar la referencia {simbolo_benchmark}: {error}\n"
                "    El informe se generará sin comparación.",
                file=sys.stderr,
            )

    # 4. Inflación (IPC de España)
    ipc = None
    ipc_meta = None
    if args.inflacion == "espana":
        try:
            ipc, ipc_meta = inflacion.cargar_ipc(sin_cache=args.sin_cache)
            print(
                _tenue(
                    f"IPC España: último dato {ipc_meta.get('ultimo_dato', '—')} "
                    f"({ipc_meta.get('fuente', 'INE')})."
                ),
                file=sys.stderr,
            )
        except inflacion.ErrorInflacion as error:
            print(
                f"⚠️  No se ha podido cargar el IPC de España: {error}\n"
                "    El informe se generará sin rentabilidad real.",
                file=sys.stderr,
            )

    # 5. Construir fichas
    fichas = [
        informe.construir_ficha(
            instrumento,
            serie,
            periodo=args.periodo,
            benchmark_serie=benchmark_serie,
            benchmark_nombre=benchmark_nombre,
            aportacion=args.aporta,
            frecuencia_aportacion=args.frecuencia_aportacion,
            tasa_libre_riesgo=args.tasa_libre_riesgo,
            ipc=ipc,
            posiciones=args.posiciones,
        )
        for instrumento, serie in fichas_base
    ]

    comparativa = informe.comparativa_cartera(
        fichas, series, args.periodo
    ) if len(fichas) > 1 else None

    # 5. Renderizar
    ruta = informe.generar(
        fichas,
        comparativa,
        benchmark_nombre,
        args.periodo,
        ruta=args.salida,
        cdn=args.cdn,
        benchmark_divisa=benchmark_divisa,
        tema=args.tema,
    )

    for ficha in fichas:
        _resumen_ficha(ficha)

    print(f"\n✅ Informe generado: {ruta}")
    print(_tenue(f"   {ruta.stat().st_size / 1024:.0f} KB · ábrelo en el navegador"))

    if args.abrir:
        webbrowser.open(ruta.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
