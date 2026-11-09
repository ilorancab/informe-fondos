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

# Fondos y ETFs habituales que se muestran como sugerencias en la web. No se
# consulta a Yahoo en cada carga: la lista vive en el repositorio y se puede
# ampliar sin tocar el código. La búsqueda en vivo es un complemento.
POPULARES = CATALOGO + [
    {
        "nombre": "iShares Core MSCI World UCITS ETF Acc",
        "isin": "IE00B4L5Y983",
        "simbolo": "IWDA.AS",
        "indice": "MSCI World",
        "gestora": "BlackRock / iShares",
        "nota": "ETF acumulativo, muy líquido y de bajo coste.",
    },
    {
        "nombre": "iShares Core S&P 500 UCITS ETF Acc",
        "isin": "IE00B5BMR087",
        "simbolo": "CSPX.AS",
        "indice": "S&P 500",
        "gestora": "BlackRock / iShares",
        "nota": "El ETF de S&P 500 más usado en Europa.",
    },
    {
        "nombre": "Vanguard S&P 500 UCITS ETF Acc",
        "isin": "IE00B3XXRP09",
        "simbolo": "VUSA.AS",
        "indice": "S&P 500",
        "gestora": "Vanguard",
        "nota": "Alternativa de bajo coste al CSPX.",
    },
    {
        "nombre": "iShares Core MSCI Emerging Markets IMI UCITS ETF Acc",
        "isin": "IE00BKM4GZ66",
        "simbolo": "EIMI.AS",
        "indice": "Emergentes",
        "gestora": "BlackRock / iShares",
        "nota": "Emergentes amplios, incluidos small caps.",
    },
    {
        "nombre": "iShares Core EURO STOXX 50 UCITS ETF Acc",
        "isin": "IE00B53L3W79",
        "simbolo": "EUE.AS",
        "indice": "Europa",
        "gestora": "BlackRock / iShares",
        "nota": "Las 50 mayores empresas de la eurozona.",
    },
    {
        "nombre": "iShares MSCI World Small Cap UCITS ETF Acc",
        "isin": "IE00BF4RFH31",
        "simbolo": "WSML.AS",
        "indice": "Small caps",
        "gestora": "BlackRock / iShares",
        "nota": "Pequeñas y medianas empresas de países desarrollados.",
    },
    {
        "nombre": "iShares Core Global Aggregate Bond UCITS ETF EUR Hedged Acc",
        "isin": "IE00BDBRDM35",
        "simbolo": "AGGH.AS",
        "indice": "Bonos",
        "gestora": "BlackRock / iShares",
        "nota": "Renta fija global cubierta a euros.",
    },
]
