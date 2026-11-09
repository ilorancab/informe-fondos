# Informe de fondos en Raspberry Pi / OMV

Esta carpeta contiene un `compose.yaml` de **solo pull**: no compila nada en la
Raspberry, descarga la imagen publicada en Docker Hub.

## Antes de empezar

- Raspberry Pi con sistema de **64 bits**. Comprueba:

  ```bash
  uname -m
  # debe devolver aarch64
  ```

- Docker y Docker Compose instalados (por ejemplo, desde el plugin de OMV).
- La imagen publicada para `linux/arm64`. Si publicas multi-arquitectura, Docker
  elige la variante correcta sola.

## Instalación

Copia esta carpeta a la Raspberry o crea estos archivos en un directorio:

```bash
mkdir -p datos salida
cp .env.example .env
```

Edita `.env` y cambia como mínimo:

```env
IMAGE=ilbravo/informe-fondos:latest
UID=1000
GID=1000
```

Si haces fork y publicas tu propia imagen, cambia `ilbravo` por tu usuario.

`UID`/`GID` deben ser los del usuario dueño de `datos/` y `salida/`. En la
Raspberry:

```bash
id -u
id -g
```

Después:

```bash
docker compose pull
docker compose up -d
```

Abre:

```text
http://IP-DE-LA-RASPBERRY:8000
```

El informe más reciente está siempre en `/ultimo`.

## Actualizar

```bash
docker compose pull
docker compose up -d
```

Si fijas una versión concreta (`:0.2.1`) no cambiará hasta que cambies `IMAGE` o
hagas `docker compose pull` con otra etiqueta.

## OMV y Portainer

Si usas Portainer, pega el contenido de `compose.yaml` como stack. Para los
volúmenes, es más seguro usar rutas absolutas de OMV, por ejemplo:

```yaml
volumes:
  - /srv/dev-disk-by-uuid-XXXXXXXX/appdata/informe-fondos/datos:/app/datos
  - /srv/dev-disk-by-uuid-XXXXXXXX/appdata/informe-fondos/salida:/app/salida
```

Asegúrate de que el usuario `UID:GID` puede escribir en esas carpetas.

## Seguridad

No expongas el puerto 8000 directamente a internet sin protección. Opciones:

- Activar HTTP Basic en `.env`:

  ```env
  WEB_USUARIO=tu_usuario
  WEB_CLAVE=una-clave-larga
  ```

- Poner Nginx Proxy Manager, Caddy, Swag o Traefik delante con HTTPS.
- Limitar el acceso a la red local/VPN.

## Problemas habituales

**`no matching manifest for linux/arm64`**

La imagen no se publicó para ARM64. Vuelve a publicarla con
`--platform linux/amd64,linux/arm64` o solo `linux/arm64`.

**La web no arranca o el healthcheck falla**

```bash
docker compose logs -f
```

En una Raspberry Pi 4 el arranque inicial puede tardar unos segundos por la
carga de pandas/numpy.

**Permisos en `datos/` o `salida/`**

Ajusta `UID`/`GID` en `.env` o cambia el propietario de las carpetas:

```bash
sudo chown -R 1000:1000 datos salida
```
