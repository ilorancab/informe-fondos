# Informe de fondos indexados

Script en Python que genera un **informe HTML autocontenido** con el estado y la
evolución de un fondo indexado o ETF. Descarga los datos de Yahoo Finance (API
pública, sin clave) y calcula rentabilidades, riesgo, caídas, rentabilidad real
frente al IPC de España y una simulación de aportaciones periódicas.

El objetivo es formativo: sirve para entender qué dicen los números de un fondo
antes de contratarlo, y de paso tener una herramienta útil de seguimiento.

## Qué incluye el informe

- **Ficha del fondo**: nombre, ISIN, símbolo, divisa, mercado e historial.
- **KPIs**: último valor, rentabilidad del año, a 1 y 3 años, volatilidad y máxima caída.
- **Gráficos interactivos**: evolución del valor, caídas desde máximos, comparación
  con un índice de referencia, rentabilidad por año y mapa de calor mes a mes.
- **Tabla de rentabilidades** por periodo (día, semana, mes, YTD, 1, 3, 5, 10 años y total).
- **Simulador de aportaciones**: «si hubiera invertido 200 € al mes, ¿cuánto tendría hoy?»
  con dinero aportado, valor actual, beneficio, rentabilidad y TIR anual. El
  importe y el ritmo (mensual, semanal o quincenal) son configurables.
- **Rentabilidad real**: descuenta el IPC general de España (INE) para ver cuánto
  ha crecido de verdad el poder de compra, con tabla por periodos y gráfico
  frente a la inflación.
- **Tema claro u oscuro**: botón en el propio informe y opción `--tema` para
  generarlo directamente en oscuro.
- **Glosario** para interpretar cada métrica.
- Aviso legal y limitaciones.

Todo el HTML (incluidos los gráficos) va en un solo archivo: se puede abrir sin
internet y compartir por correo.

## Requisitos

- Python 3.11 o superior.
- Conexión a internet la primera vez (después se usa una caché local de 6 horas).
- [uv](https://docs.astral.sh/uv/) (recomendado) o `pip`.
- Docker y Docker Compose (opcional, para la versión web).

## Instalación

Con `uv`:

```bash
cd informe-fondos
uv sync
```

Con `pip`:

```bash
cd informe-fondos
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Ambos instalan el paquete y el comando `informe-fondos`. Ejecuta los comandos
desde la raíz del proyecto para que `.env`, `datos/` y `salida/` se resuelvan
ahí. También puedes usar `uv run python -m informe_fondos`.

## Uso

Lo más simple, con un ISIN:

```bash
uv run informe-fondos IE00B03HCZ61
```

Al terminar se imprime un resumen en la terminal y se guarda el HTML en
`salida/`. Para abrirlo automáticamente en el navegador:

```bash
uv run informe-fondos IE00B03HCZ61 --abrir
```

### Elegir periodo y aportación

```bash
uv run informe-fondos IE00B03HCZ61 --periodo 3a --aporta 300
uv run informe-fondos IE00B03HCZ61 --aporta 50 --frecuencia-aportacion semanal
```

`--periodo` acepta `1m`, `3m`, `6m`, `ytd`, `1a`, `2a`, `3a`, `5a`, `7a`,
`10a` y `max`. Por defecto: `5a`.

`--aporta` fija el importe y `--frecuencia-aportacion` el ritmo: `mensual`
(por defecto), `semanal` o `quincenal`.

### Añadir la inflación

El IPC de España se incluye por defecto. Para desactivarlo:

```bash
uv run informe-fondos IE00B03HCZ61 --sin-inflacion
```

O de forma explícita:

```bash
uv run informe-fondos IE00B03HCZ61 --inflacion espana
uv run informe-fondos IE00B03HCZ61 --inflacion ninguna
```

### Comparar varios fondos

```bash
uv run informe-fondos IE00B03HCZ61 IE0032620787 --abrir
```

Genera una comparativa normalizada a 100 y una ficha completa de cada fondo.

### Ver el catálogo de fondos típicos

```bash
uv run informe-fondos --listar          # solo muestra la lista
uv run informe-fondos --catalogo        # informe de todos ellos
```

### Cambiar el índice de referencia

Por defecto se compara con `IWDA.AS` (iShares Core MSCI World, en EUR). Se puede
cambiar con `--benchmark` o desactivar con `--sin-benchmark`:

```bash
uv run informe-fondos IE00B03HCZ61 --benchmark SXR8.DE
uv run informe-fondos IE00B03HCZ61 --sin-benchmark
```

### Tema claro u oscuro

El informe incluye un botón en la esquina superior derecha para cambiar entre
tema claro y oscuro sin volver a generarlo. La elección se recuerda en el
navegador.

También puedes fijar el tema al generarlo:

```bash
uv run informe-fondos IE00B03HCZ61 --tema oscuro
uv run informe-fondos IE00B03HCZ61 --tema claro
uv run informe-fondos IE00B03HCZ61 --tema auto   # sigue al sistema
```

### Otras opciones

| Opción | Para qué sirve |
| --- | --- |
| `--aporta 50` | Aportación periódica del simulador. |
| `--frecuencia-aportacion semanal` | Ritmo de las aportaciones: `mensual`, `semanal` o `quincenal`. |
| `--inflacion espana` | Añadir la rentabilidad real con el IPC de España (por defecto). |
| `--sin-inflacion` | Generar el informe solo con rentabilidades nominales. |
| `--salida ruta.html` | Elegir dónde se guarda el informe. |
| `--simbolo 0P00000RQC.F` | Forzar un símbolo de Yahoo si un ISIN es ambiguo. |
| `--sin-cache` | Volver a descargar los datos ignorando la caché. |
| `--cdn` | Cargar Plotly desde internet: el HTML pasa de ~5 MB a ~60 KB. |
| `--tema oscuro` | Generar el informe en tema oscuro (`claro`, `oscuro` o `auto`). |
| `--tasa-libre-riesgo 3` | Tasa libre de riesgo anual (%) para el ratio de Sharpe. |

## Web y Docker

Además del CLI, el proyecto incluye una interfaz web para generar los informes
desde el navegador.

### Arrancar con Docker

```bash
cp .env.example .env   # solo la primera vez; ajusta tus valores
mkdir -p datos salida
docker compose up --build -d
```

Abre <http://localhost:8000>. Desde ahí puedes elegir ISIN, periodo, aportación,
frecuencia, tema e inflación, generar el informe y abrirlo, descargarlo o
borrarlo. La ruta `/ultimo` redirige siempre al informe más reciente, útil para
marcadores.

- Los informes se guardan en `salida/` y la caché en `datos/`; ambos directorios
  están montados como volúmenes, así que sobreviven a reinicios y los ves desde
  el host.
- Los archivos se crean con tu usuario del host. Si tu UID/GID no es `1000`,
  cámbialo en `.env` (`UID=$(id -u)`, `GID=$(id -g)`).
- Cambia el puerto con `PUERTO=8080` en `.env`.
- Ver logs: `docker compose logs -f`.
- Parar: `docker compose down`.
- Actualizar tras cambios: `docker compose up --build -d`.

La web usa `--cdn` por defecto para que los informes ocupen menos. Si desmarcas
«HTML ligero», se genera un archivo autocontenido de unos 5 MB que funciona sin
internet. El CLI sigue generando HTML autocontenido por defecto.

### Proteger el acceso

Si la web va a estar accesible desde fuera de tu red, activa HTTP Basic y ponla
detrás de HTTPS (Caddy, Nginx, Traefik...). En `.env`:

```env
WEB_USUARIO=tu_usuario
WEB_CLAVE=una-clave-larga
```

Sin esas variables no hay login. No expongas el puerto directamente a internet
sin autenticación: cualquiera podría lanzar generaciones y consumir tu cuota de
Yahoo o del INE.

### Sin Docker

```bash
uv sync
uv run uvicorn informe_fondos.web.app:app --host 127.0.0.1 --port 8000 --reload
```

La web usa el mismo CLI internamente, así que respeta `.env` y las mismas
opciones. El informe generado se sirve en `/informes/<archivo>.html`.

La imagen de referencia está publicada en `ilbravo/informe-fondos`:

## Publicar en Docker Hub

La imagen está pensada para publicarse **multi-arquitectura** (`linux/amd64` y
`linux/arm64`). Así la Raspberry Pi 4 descarga sola la variante ARM64.

1. Crea el repositorio `TU_USUARIO/informe-fondos` en Docker Hub.
2. Inicia sesión con un token de acceso:

   ```bash
   docker login
   ```

3. Prepara buildx. En Linux, para poder construir ARM64 desde tu equipo x86:

   ```bash
   docker run --privileged --rm tonistiigi/binfmt --install arm64
   make buildx
   ```

4. Compila y publica:

   ```bash
   make push IMAGE=TU_USUARIO/informe-fondos TAG=0.2.1
   ```

   Esto sube `0.2.1` y también actualiza `latest`.

5. Comprueba que existen las dos arquitecturas:

   ```bash
   docker buildx imagetools inspect TU_USUARIO/informe-fondos:latest
   ```

   Debe aparecer `linux/amd64` y `linux/arm64`.

También puedes construirla directamente en la Raspberry, sin QEMU:

```bash
docker buildx build --platform linux/arm64 \
  -t TU_USUARIO/informe-fondos:latest \
  -f docker/Dockerfile --push .
```

### Publicación automática con GitHub Actions

El repositorio incluye `.github/workflows/docker.yml`. Si lo subes a GitHub,
define estos secretos en **Settings → Secrets and variables → Actions**:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (token de acceso, no tu contraseña)

Cada push a `main`/`master` o etiqueta `v*` ejecutará las pruebas y publicará la
imagen multi-arquitectura. También se puede lanzar manualmente con
`workflow_dispatch`.

### Desplegar en la Raspberry Pi / OMV

La carpeta `deploy/pi/` contiene un compose de solo pull, pensado para la
Raspberry. Instrucciones completas en [`deploy/pi/README.md`](deploy/pi/README.md).

Resumen:

```bash
mkdir -p datos salida
cp .env.example .env
# edita .env: IMAGE, UID, GID, PUERTO...
docker compose pull
docker compose up -d
```

## Cómo funciona

1. **Identificación.** Un ISIN es el código de 12 caracteres que identifica un
   fondo en todo el mundo (por ejemplo, `IE00B03HCZ61`). Un *ticker* es el código
   de cotización en un mercado concreto (por ejemplo, `IWDA.AS`).
2. **Resolución.** Si se pasa un ISIN, se busca en Yahoo Finance y se elige la
   cotización más adecuada (fondo antes que ETF, mercados europeos primero). La
   equivalencia se guarda en `datos/simbolos.json`.
3. **Descarga.** Se pide la serie histórica completa con fechas explícitas
   (`period1`/`period2`) para que Yahoo devuelva datos **diarios** de verdad, no
   una serie agregada. Se usa el precio ajustado por dividendos y se guarda en
   `datos/series/` durante 6 horas. La caché lleva un número de versión: al
   cambiar el formato, las series antiguas se descargan de nuevo.
4. **Inflación.** Se descarga el IPC general nacional del INE (serie `IPC290751`,
   base 2021), se guarda una semana en `datos/ipc.json` y se calcula la
   rentabilidad real de cada periodo.
5. **Análisis.** Se calculan rentabilidades, volatilidad anualizada, drawdown
   histórico, Sharpe y la simulación de aportaciones (mensuales, semanales o
   quincenales).
6. **Informe.** Jinja2 rellena la plantilla y Plotly dibuja los gráficos. El
   JavaScript de Plotly se incrusta en el HTML para que sea autocontenido.

## Estructura

```
informe-fondos/
├── src/informe_fondos/
│   ├── __main__.py          # python -m informe_fondos
│   ├── cli.py               # punto de entrada y argumentos
│   ├── config.py            # rutas, caché y valores por defecto
│   ├── catalogo.py          # fondos de referencia (ISIN verificados)
│   ├── datos/
│   │   ├── fuentes.py       # Yahoo Finance: resolución y descarga
│   │   └── inflacion.py     # IPC de España (INE)
│   ├── analisis/
│   │   ├── metricas.py      # rentabilidades, riesgo y drawdown
│   │   ├── dca.py           # simulación de aportaciones
│   │   └── comparacion.py   # índice de referencia, correlación y beta
│   ├── presentacion/
│   │   ├── formato.py       # números y fechas en formato español
│   │   ├── graficos.py      # figuras de Plotly
│   │   ├── informe.py       # contexto y renderizado con Jinja2
│   │   └── plantillas/
│   │       └── informe.html.j2
│   └── web/
│       ├── app.py           # FastAPI: formulario, generación y descarga
│       └── templates/
│           └── index.html
├── tests/                   # pruebas con pytest
├── deploy/
│   └── pi/
│       ├── compose.yaml     # despliegue con variables/.env
│       ├── .env.example
│       └── README.md
├── .github/
│   └── workflows/
│       └── docker.yml       # publicación multi-arquitectura
├── docker/
│   └── Dockerfile           # imagen de la web
├── compose.yaml             # web + volúmenes de datos y salida
├── Makefile                 # atajos: test, web, docker...
├── pyproject.toml           # paquete, dependencias y comando
├── requirements.txt         # dependencias para instalaciones con pip
├── .env.example
├── LICENSE                  # licencia MIT
├── THIRD_PARTY_NOTICES.md   # licencias de terceros
├── datos/                   # caché de descargas (se crea sola)
└── salida/                  # informes generados (se crea sola)
```

El código está en `src/informe_fondos/` y el proyecto se instala como paquete.
Así los imports no dependen de desde qué carpeta se ejecute el comando y el CLI
queda disponible como `informe-fondos`.

## Limitaciones que conviene conocer

- **Yahoo Finance no es una fuente oficial.** Los valores liquidativos pueden
  llegar con un día de retraso y, en fondos pequeños, con más. El informe siempre
  muestra la fecha del último dato.
- **Comisiones e impuestos no están incluidos.** Las series de Yahoo suelen ser
  netas de comisiones del fondo, pero la compra, el reembolso y los impuestos
  dependen de tu plataforma y de tu situación fiscal.
- **Divisas.** El informe trabaja en la divisa del instrumento. La referencia
  por defecto, `IWDA.AS`, cotiza en EUR aunque su nombre comercial diga «USD
  (Acc)»: el precio que se compara ya está en euros. Si eliges otra referencia,
  el informe muestra su divisa junto al nombre.
- **Frecuencia de los datos.** Yahoo puede devolver la serie agregada (semanal o
  mensual) si se pide `range=max`; el programa fuerza datos diarios. Si el fondo
  solo publica valor liquidativo semanal o mensual, se detecta y la volatilidad
  se anualiza con la frecuencia real (52 observaciones al año si es semanal, 12
  si es mensual), no con 252 sesiones. La ficha muestra un chip con la frecuencia.
- **Años naturales.** Se calculan con el último dato disponible de cada año. Si
  Yahoo no tiene el valor del 31/12, la cifra puede diferir unas décimas de la
  ficha oficial de la gestora.
- **IPC.** El INE publica el IPC con unas semanas de retraso. La rentabilidad real
  se calcula hasta el último dato disponible y el informe indica su fecha. La
  serie homogénea del INE empieza en 2002; para periodos anteriores no se muestra
  rentabilidad real.
- **El simulador es una aproximación.** Compra el primer día hábil de cada mes,
  semana o quincena al valor liquidativo de ese día, sin comisiones ni
  retenciones.
- **No es asesoramiento financiero.** Es una herramienta para aprender y observar;
  las decisiones son tuyas.

## Solución de problemas

**«Yahoo Finance está limitando las peticiones (error 429)»**

Yahoo limita el número de peticiones por dirección IP. Espera 10-15 minutos y
vuelve a intentarlo. La caché de `datos/` evita repetir descargas ya hechas, así
que no uses `--sin-cache` salvo que necesites datos frescos.

**El ISIN no aparece en Yahoo**

Prueba con el ticker como alternativa (`--simbolo 0P00000RQC.F`). Puedes
encontrar el ticker en la ficha de Morningstar del fondo. También puedes pasar el
ticker directamente como identificador.

Si el ISIN sí aparece pero falla la descarga, el programa vuelve a resolverlo
automáticamente descartando la caché de símbolos: Yahoo a veces lista la misma
clase del fondo en varios mercados y alguno de ellos no tiene histórico. En el
ejemplo de `IE00BYX5NX33`, el símbolo bueno es `0P0001CLDK.F` (Frankfurt), no
`IE00BYX5NX33.SG` (Stuttgart).

**El informe se genera sin la comparación con el índice**

El benchmark por defecto es `IWDA.AS`. Si falla su descarga, el informe se genera
igualmente sin esa sección. Puedes elegir otro con `--benchmark` o quitarlo con
`--sin-benchmark`.

**El HTML pesa mucho**

Por defecto Plotly se incrusta en el archivo (unos 5 MB) para que funcione sin
internet. Con `--cdn` el HTML baja a unos cientos de KB, pero necesita conexión
para mostrar los gráficos.

**Quiero empezar de cero**

Borra la carpeta `datos/`. Se volverá a crear con las próximas descargas.

## Desarrollo

```bash
uv sync                 # instala el paquete y las dependencias
uv run pytest           # pruebas de los cálculos
uv run uvicorn informe_fondos.web.app:app --reload
```

O con el `Makefile`:

```bash
make install   # uv sync
make test      # uv run pytest
make web       # servidor de desarrollo en :8000
make up        # docker compose up --build -d
make logs
make down
```

El paquete está en `src/informe_fondos/`. Si añades un módulo, usa imports
relativos dentro del paquete (`from ..datos import fuentes`) y ejecuta las pruebas
antes de reconstruir Docker.

## Ideas para seguir aprendiendo

- Incluir el TER y el *tracking error* del fondo.
- Enviar el informe por correo una vez al mes (reutilizando `enviar-clima`).
- Guardar una cartera personal con participaciones y precios de compra.
- Exportar también a PDF con WeasyPrint.

## Variables de entorno (opcional)

Crea un `.env` en la raíz del proyecto si quieres cambiar los valores por defecto:

```env
BENCHMARK=IWDA.AS
APORTACION_PERIODICA=200
FRECUENCIA_APORTACION=mensual
INFLACION=espana
TEMA=auto
TASA_LIBRE_RIESGO=2
```

Así el simulador usa esos valores por defecto, sin repetir las opciones en
cada ejecución. `APORTACION_MENSUAL` se sigue aceptando como nombre antiguo.

Si ejecutas el comando desde otra carpeta, define `INFORME_FONDOS_HOME` con la
ruta del proyecto: allí se buscarán `.env`, `datos/` y `salida/`.

```bash
INFORME_FONDOS_HOME=/ruta/a/informe-fondos uv run informe-fondos IE00B03HCZ61
```

## Licencia

Este proyecto se distribuye bajo licencia **MIT**. Consulta [`LICENSE`](LICENSE).

Los componentes de terceros y sus licencias están resumidos en
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). La imagen Docker incluye
ambos archivos en `/app`.

## Aviso

Proyecto independiente y formativo. No está afiliado, patrocinado ni respaldado
por Vanguard, BlackRock, iShares, MSCI, Amundi, Fidelity ni por ninguna gestora
o plataforma. Las marcas citadas pertenecen a sus propietarios.

No constituye asesoramiento financiero ni una recomendación de compra o venta.
