"""Catálogo de fondos indexados habituales en plataformas españolas.

Todos los ISIN y símbolos están verificados contra Yahoo Finance. Incluir el
símbolo evita la petición de búsqueda (la más limitada por Yahoo) y hace que
estos fondos funcionen incluso cuando la búsqueda por ISIN falla.

El catálogo es solo una ayuda para empezar: cualquier ISIN o ticker se puede
pasar por línea de comandos sin tocar este archivo.
"""

CATALOGO = [
    {
        "nombre": "Vanguard Global Stock Index Fund Investor EUR Acc",
        "isin": "IE00B03HCZ61",
        "simbolo": "0P00000RQC.F",
        "indice": "MSCI World",
        "gestora": "Vanguard",
        "nota": "El «todo mundo desarrollado» clásico; TER bajo.",
    },
    {
        "nombre": "iShares Developed World Index Fund (IE) D Acc EUR",
        "isin": "IE00BD0NCM55",
        "simbolo": "0P0001AINF.F",
        "indice": "MSCI World",
        "gestora": "BlackRock / iShares",
        "nota": "Alternativa a Vanguard Global, también de bajo coste.",
    },
    {
        "nombre": "Amundi Index MSCI World AE-C",
        "isin": "LU0996182563",
        "simbolo": "0P00012PP6.F",
        "indice": "MSCI World",
        "gestora": "Amundi",
        "nota": "Clase con historial largo y comisión competitiva.",
    },
    {
        "nombre": "Fidelity MSCI World Index Fund P-Acc-EUR",
        "isin": "IE00BYX5NX33",
        "simbolo": "0P0001CLDK.F",
        "indice": "MSCI World",
        "gestora": "Fidelity",
        "nota": "Otra opción global desarrollada.",
    },
    {
        "nombre": "Vanguard U.S. 500 Stock Index Fund Investor EUR Acc",
        "isin": "IE0032620787",
        "simbolo": "0P00000G12.F",
        "indice": "S&P 500",
        "gestora": "Vanguard",
        "nota": "Solo las 500 mayores empresas de EE. UU.; más concentrado.",
    },
]
