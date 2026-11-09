# Avisos de terceros

`informe-fondos` usa software de terceros. Este archivo resume las licencias
principales; los textos completos están en los metadatos de cada paquete y, en
la imagen Docker, en los directorios `*.dist-info/licenses` de Python y en
`/usr/share/doc` del sistema base Debian.

## Componentes principales

| Componente | Versión | Licencia |
| --- | ---: | --- |
| Python | 3.13 | PSF-2.0 |
| FastAPI | 0.162.2 | MIT |
| Starlette | 1.10.0 | BSD-3-Clause |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| Pydantic | 2.14.3 | MIT |
| Jinja2 | 3.1.6 | BSD-3-Clause |
| pandas | 3.1.1 | BSD-3-Clause |
| NumPy | 2.5.4 | BSD-3-Clause y otras licencias permisivas |
| Plotly | 7.1.0 | MIT |
| narwhals | 2.28.0 | MIT |
| python-dateutil | 4.0.0 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| httptools | 0.9.0 | MIT |
| uvloop | 0.23.0 | MIT |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.4 | BSD-3-Clause |
| anyio | 4.16.0 | MIT |
| h11 | 0.16.0 | MIT |
| click | 8.5.1 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| packaging | 26.3 | Apache-2.0 o BSD-2-Clause |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| tzdata | 2026.6 | Apache-2.0 |

La imagen base `python:3.13-slim` incluye Debian y sus paquetes, cada uno con su
propia licencia. Consulta `/usr/share/doc` dentro del contenedor para los textos
completos.

## Fuentes de datos

- **Yahoo Finance**: los datos de mercado no se redistribuyen con la imagen; se
  consultan en tiempo de ejecución. La API utilizada no es oficial.
- **INE**: el IPC procede del Instituto Nacional de Estadística. Los datos del
  INE son públicos; el informe cita la fuente.

## Marcas

Vanguard, iShares, BlackRock, MSCI, Amundi, Fidelity y el resto de nombres de
fondos o índices son marcas de sus respectivos propietarios. Este proyecto es
independiente y no está afiliado, patrocinado ni respaldado por ninguna de esas
entidades.

## Aviso

Este archivo es informativo y no constituye asesoramiento legal. Si vas a
distribuir la imagen comercialmente, revisa las licencias y los términos de uso
de cada componente y de las fuentes de datos.
