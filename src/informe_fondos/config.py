"""Configuración general del proyecto.

Los valores por defecto se pueden cambiar con variables de entorno o con un
archivo `.env` en la raíz del proyecto (formato CLAVE=valor). Las variables de
entorno reales tienen prioridad sobre el archivo.

Variables reconocidas:
    INFORME_FONDOS_HOME    Carpeta de datos y salida (por defecto, el directorio actual).
    BENCHMARK              Símbolo de Yahoo del índice de referencia.
    APORTACION_PERIODICA   Importe de la aportación del simulador (€).
    FRECUENCIA_APORTACION  Ritmo: mensual, semanal o quincenal.
    INFLACION              espana (IPC del INE) o ninguna.
    TEMA                   auto, claro u oscuro.
    TASA_LIBRE_RIESGO      Rentabilidad del activo sin riesgo, en % anual.
"""

import os
from pathlib import Path

HOME = Path(
    os.environ.get("INFORME_FONDOS_HOME", Path.cwd())
).expanduser().resolve()
DATOS = HOME / "datos"
SERIES = DATOS / "series"
SALIDA = HOME / "salida"
PLANTILLAS = Path(__file__).resolve().parent / "presentacion" / "plantillas"
ARCHIVO_ENV = HOME / ".env"

# Yahoo Finance rechaza peticiones sin un User-Agent de navegador.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Horas que se reutiliza una descarga antes de volver a pedirla.
HORAS_CACHE = 6

# El IPC se publica una vez al mes; no hace falta pedirlo a diario.
HORAS_CACHE_IPC = 24 * 7

# Versión del formato de caché. Al cambiarla se invalidan las series antiguas
# (por ejemplo, las que Yahoo devolvió agregadas en vez de diarias).
VERSION_CACHE = 2

# Índice de referencia por defecto: iShares Core MSCI World (ETF en EUR).
BENCHMARK_POR_DEFECTO = "IWDA.AS"

# Valores por defecto del simulador y de las métricas.
APORTACION_POR_DEFECTO = 200.0
FRECUENCIA_APORTACION_POR_DEFECTO = "mensual"
TASA_LIBRE_RIESGO_POR_DEFECTO = 2.0
TEMA_POR_DEFECTO = "auto"

# Paleta usada en gráficos e informe.
COLORES = {
    "principal": "#0d9488",
    "secundario": "#d97706",
    "positivo": "#16a34a",
    "negativo": "#dc2626",
    "neutro": "#64748b",
    "serie": ["#0d9488", "#d97706", "#2563eb", "#7c3aed", "#db2777", "#0891b2"],
}


def cargar_env(archivo=ARCHIVO_ENV):
    """Carga un archivo .env sencillo sin dependencias externas."""
    if not archivo.exists():
        return

    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue

        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip()

        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            valor = valor[1:-1]

        os.environ.setdefault(clave, valor)


def valor_env(clave, defecto):
    """Devuelve una variable de entorno como texto, o el valor por defecto."""
    cargar_env()
    return os.environ.get(clave, "").strip() or defecto
