# Imágenes de Docker

Infraestructuras Paralelas y Distribuidas
Escuela de Ingeniería de Sistemas y Computación, Universidad del Valle
Carlos Andrés Delgado Saavedra

Lo que cada parte necesita de las bibliotecas y herramientas está en
[DOCUMENTACION.md](DOCUMENTACION.md), con ejemplos que corren y los enlaces
a la documentación oficial.

Un servicio pequeño ya escrito y una imagen por construir. El código de la
aplicación no se toca: lo que se entrega es el empaquetado.

## La aplicación

`app/servidor.py` es un servicio Flask con dos rutas: `/` devuelve un saludo y
el número de visitas, y `/health` devuelve `{"status": "ok"}`. Escucha en el
puerto 8000 y lee dos variables de ambiente, `PORT` y `SALUDO`.

## Requisitos

| Qué | Linux (Debian/Ubuntu) | macOS | Windows |
|---|---|---|---|
| Docker Engine | repositorio oficial de Docker, según [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) | Docker Desktop | Docker Desktop, sobre WSL2 |
| `curl`, para probar el servicio | `sudo apt install curl` | viene con el sistema | viene con Windows 10 y 11 |

En Linux, después de instalar, `sudo usermod -aG docker $USER` y volver a
iniciar sesión evita el `sudo` en cada `docker`. En macOS y Windows, Docker
Desktop tiene que estar abierto para que el comando `docker` responda. La
imagen que se construye es la misma en los tres sistemas; en un Mac con
Apple Silicon se construye para ARM y el servidor de Actions la vuelve a
construir para x86-64, así que el `Dockerfile` no debe depender de la
arquitectura.

Los detalles de cada sistema están en
[DOCUMENTACION.md](DOCUMENTACION.md), al final.

## Lo que hay que entregar

Dos archivos en la raíz del repositorio:

1. `Dockerfile` que empaquete el servicio.
2. `.dockerignore` que deje por fuera lo que no debe entrar en la imagen.

## Lo que la imagen tiene que cumplir

- Arrancar el servicio y responder en el puerto 8000.
- Correr con un usuario que no sea `root`. Un contenedor comprometido que corre
  como root es una escalada de privilegios servida en bandeja.
- Pesar menos de 300 MB. Con `python:3.11-slim` sobra; con la imagen completa
  de Python, no.
- Instalar las dependencias desde `app/requirements.txt`, no a mano.

## Probar en la máquina propia

```bash
docker build -t imagenes .
docker run --rm -d --name servicio -p 8000:8000 imagenes
curl http://localhost:8000/health
curl http://localhost:8000/
docker exec servicio whoami        # no debe decir root
docker image inspect imagenes --format '{{.Size}}'
docker rm -f servicio
```

## Qué revisa el flujo de Actions

Que exista el `.dockerignore`, que la imagen construya, que el servicio
responda en las dos rutas, que el proceso no corra como root y que la imagen
no pase de 300 MB.

## Para pensar

Cada instrucción del `Dockerfile` es una capa, y las capas se reutilizan
mientras no cambie lo que hay encima. Copiar primero `requirements.txt` e
instalar, y solo después copiar el código, hace que un cambio en el código no
obligue a reinstalar todo. Vale la pena construir dos veces y mirar cuáles
pasos dicen `CACHED`.
