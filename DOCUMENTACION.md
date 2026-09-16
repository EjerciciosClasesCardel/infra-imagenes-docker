# Documentación de apoyo: imágenes de Docker

Aquí está lo que hace falta para escribir el `Dockerfile` y el `.dockerignore`
que pide el README: la aplicación Flask que se empaqueta, cada instrucción del
`Dockerfile`, el archivo de exclusiones, los comandos para construir y revisar
la imagen, y cómo se comportan las capas y la caché. Los ejemplos corren tal
cual, resuelven un problema vecino al del ejercicio y traen su salida real; los
enlaces a la documentación van al final de cada sección.

Las partes van en el orden de los apartados del README. *La aplicación* es la
parte 1; *Lo que hay que entregar*, las partes 2 y 3, un archivo por parte. Lo
que la imagen tiene que cumplir se reparte: el usuario sin privilegios, la
imagen base liviana y la instalación desde `requirements.txt` están en la parte
2, y el puerto 8000 publicado en la parte 4, que también cubre *Probar en la
máquina propia* y lo que revisa el flujo de Actions. *Para pensar* es la parte
5. Cierra cómo instalar Docker en cada sistema operativo.

## Parte 1: la aplicación

El código de `app/servidor.py` no se modifica, pero hay que entender qué hace
para empaquetarlo: en qué puerto escucha, en qué dirección, qué variables de
ambiente lee y con qué se arranca.

### Lo que se usa

- `Flask(__name__)`: crea la aplicación. El nombre del módulo le sirve para
  ubicar plantillas y archivos estáticos; para un servicio JSON basta con
  pasarlo y seguir.
- `@app.get("/ruta")`: registra la función que responde a `GET /ruta`. Es la
  forma corta de `@app.route("/ruta", methods=["GET"])`.
- `jsonify(clave=valor, ...)`: arma la respuesta JSON y le pone el encabezado
  `Content-Type: application/json`. Recibe los campos como argumentos con
  nombre o un diccionario.
- `app.run(host="0.0.0.0", port=8000)`: arranca el servidor de desarrollo de
  Werkzeug. Sin `host`, escucha en `127.0.0.1` y solo acepta conexiones desde
  la misma máquina; dentro de un contenedor, la misma máquina es el contenedor
  y desde afuera no llega nada. `0.0.0.0` escucha en todas las interfaces.
- `os.environ.get("VAR", "valor por defecto")`: lee una variable de ambiente
  como texto. El puerto se pasa por `int()` antes de usarlo.
- `gunicorn --bind 0.0.0.0:PUERTO [--workers N] modulo:objeto`: servidor WSGI
  para producción; está en `app/requirements.txt` por eso. `modulo` es el
  archivo sin `.py` y `objeto` es la variable que guarda la aplicación. Se
  ejecuta desde el directorio donde está el módulo, o se le pasa
  `--chdir`. Con gunicorn el puerto lo fija `--bind`; la variable `PORT` solo
  la lee `app.run`.

### Ejemplo

Un servicio vecino: responde la hora del servidor y cuenta cuántas veces se la
pidieron. Lee `PORT` y `ZONA` del ambiente.

```python
"""Servicio que responde la hora del servidor y cuenta cuántas veces se la pidieron."""
import os
from datetime import datetime

from flask import Flask, jsonify

app = Flask(__name__)
CONSULTAS = {"total": 0}
ZONA = os.environ.get("ZONA", "servidor")


@app.get("/hora")
def hora():
    CONSULTAS["total"] += 1
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(zona=ZONA, hora=ahora, consultas=CONSULTAS["total"])


@app.get("/ping")
def ping():
    return jsonify(pong=True)


if __name__ == "__main__":
    # 0.0.0.0 acepta conexiones desde cualquier interfaz, no solo desde localhost
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "9000")))
```

Se guarda como `reloj.py`, se instala Flask en un entorno virtual y se arranca
en segundo plano para consultarlo con `curl`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask==3.0.3 gunicorn==22.0.0
PORT=9001 python reloj.py &
curl http://localhost:9001/ping
curl http://localhost:9001/hora
curl http://localhost:9001/hora
```

Salida, sin la línea con la dirección de la red local:

```
 * Serving Flask app 'reloj'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:9001
Press CTRL+C to quit
{"pong":true}
{"consultas":1,"hora":"2026-09-16 14:27:29","zona":"servidor"}
{"consultas":2,"hora":"2026-09-16 14:27:29","zona":"servidor"}
```

La advertencia del servidor de desarrollo es la razón de que gunicorn esté en
las dependencias. El mismo módulo, servido con gunicorn:

```bash
ZONA=Bogota gunicorn --bind 0.0.0.0:9002 --workers 1 reloj:app &
curl http://localhost:9002/hora
```

```
[2026-09-16 14:27:35 -0500] [95656] [INFO] Starting gunicorn 22.0.0
[2026-09-16 14:27:35 -0500] [95656] [INFO] Listening at: http://0.0.0.0:9002 (95656)
[2026-09-16 14:27:35 -0500] [95656] [INFO] Using worker: sync
[2026-09-16 14:27:35 -0500] [95694] [INFO] Booting worker with pid: 95694
{"consultas":1,"hora":"2026-09-16 14:27:37","zona":"Bogota"}
```

### Lo que suele fallar

- **Escuchar en `127.0.0.1` dentro del contenedor.** Síntoma: el contenedor
  está `Up`, `docker logs` muestra el servidor arrancado, y desde la máquina
  `curl` responde `curl: (56) Recv failure: Connection reset by peer`. Causa:
  el servidor acepta conexiones solo desde la interfaz interna del contenedor
  y la publicación de puertos llega por otra. Va `0.0.0.0`.
- **Arrancar gunicorn desde el directorio equivocado.** El worker muere con
  `ModuleNotFoundError: No module named 'reloj'`, porque `modulo:objeto` se
  resuelve desde el directorio actual. En el `Dockerfile` ese directorio lo
  decide `WORKDIR`.
- **Instalar las dependencias a mano y sin versión.** `pip install flask` trae
  la última versión, no la que está en `requirements.txt`, y el flujo de
  Actions y la máquina propia terminan con paquetes distintos. Se instala
  con `-r requirements.txt` y ya.
- **Confundir el puerto de la aplicación con el publicado.** La aplicación
  escucha en el puerto que dice `PORT` o `--bind`; que ese puerto se vea
  desde afuera lo decide `docker run -p`. Son dos decisiones distintas y las
  dos tienen que apuntar al 8000.

### Enlaces

- [Flask, guía de inicio](https://flask.palletsprojects.com/en/stable/quickstart/):
  rutas, respuestas JSON y cómo arrancar la aplicación.
- [Flask, referencia de la API](https://flask.palletsprojects.com/en/stable/api/):
  firma de `Flask.run`, con los parámetros `host` y `port`, y de `jsonify`.
- [Flask, despliegue con gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/):
  cómo se le pasa la aplicación a gunicorn y por qué no se usa `app.run` en producción.
- [Gunicorn, inicio rápido](https://docs.gunicorn.org/quickstart/):
  la forma `modulo:objeto` y las opciones más usadas.
- [Gunicorn, referencia de opciones](https://docs.gunicorn.org/reference/settings/):
  `--bind`, `--workers`, `--chdir` y el resto de banderas.
- [`os.environ` en Python](https://docs.python.org/3/library/os.html):
  cómo se leen las variables de ambiente y qué pasa cuando no existen.

## Parte 2: el Dockerfile

Cada línea del `Dockerfile` es una instrucción que produce una capa de la
imagen. Aquí están las que el ejercicio necesita, con su firma y lo que hacen.

### Lo que se usa

- `FROM imagen:etiqueta`: primera instrucción; fija la imagen base sobre la
  que se construye todo. `python:3.11-slim` es Debian recortado con Python
  3.11 ya instalado. Con `docker image inspect`, `python:3.11` completa pesa 1521 MB
  porque trae compiladores y bibliotecas de desarrollo; `python:3.11-slim`,
  177 MB, y `python:3.11-alpine`, 88 MB. La alpine usa musl en vez de glibc
  y hay ruedas de pip que no le sirven; para el límite de 300 MB del
  ejercicio, la slim sobra.
- `WORKDIR /ruta`: fija el directorio de trabajo para las instrucciones que
  siguen y para el proceso del contenedor; lo crea si no existe. Reemplaza
  al `cd` y a las rutas completas repetidas.
- `COPY origen destino`: copia archivos del contexto de construcción (la
  carpeta donde está el `Dockerfile`) a la imagen. `origen` es relativo al
  contexto; `destino` relativo al `WORKDIR` si no empieza por `/`. Copiar
  una carpeta con barra final, `COPY app/ app/`, copia su contenido dentro
  de `app/`.
- `RUN comando`: ejecuta el comando durante la construcción y guarda el
  resultado como capa. Con `apt-get`, la forma que no infla la imagen es
  una sola instrucción con `update`, `install -y --no-install-recommends` y
  `rm -rf /var/lib/apt/lists/*` encadenados con `&&`. Con pip,
  `pip install --no-cache-dir -r requirements.txt` instala lo que dice el
  archivo sin dejar la caché de descargas dentro de la capa. Este ejercicio
  no necesita nada de `apt-get`: Flask y gunicorn son ruedas puras de
  Python.
- `ENV NOMBRE=valor`: define una variable de ambiente que queda en la imagen
  y que el proceso lee en tiempo de ejecución. `docker run -e NOMBRE=otro`
  la sobreescribe.
- `EXPOSE puerto`: documenta en qué puerto escucha el servicio. Es
  información para quien lee la imagen y para `docker inspect`; la
  publicación real la hace `docker run -p`.
- `USER nombre`: todas las instrucciones que siguen y el proceso del
  contenedor corren como ese usuario. El usuario tiene que existir en la
  imagen, así que antes va un `RUN` que lo cree:
  `useradd --create-home --shell /bin/bash nombre` (paquete `passwd`,
  presente en la slim) o `adduser --disabled-password --gecos "" nombre`
  (la versión de Debian pregunta contraseña y datos si no se le pasan esas
  banderas). El `RUN` de pip va antes del `USER`, para que instale en el
  sitio del sistema y no en `~/.local`.
- `CMD ["programa", "arg1", "arg2"]`: el comando que arranca cuando el
  contenedor inicia. Solo cuenta el último `CMD` del archivo. Lo que se
  escriba después del nombre de la imagen en `docker run` lo reemplaza
  entero.
- `ENTRYPOINT ["programa"]`: fija el programa del contenedor; lo que se pase
  en `docker run` no lo reemplaza sino que se agrega como argumentos. Con
  `ENTRYPOINT` y `CMD` juntos, `CMD` son los argumentos por defecto. Para
  un servicio que siempre arranca igual, `CMD` solo es suficiente.
- Forma exec y forma shell: `CMD ["python", "servidor.py"]` (lista JSON,
  comillas dobles) arranca `python` como proceso 1 del contenedor y le
  llegan las señales de `docker stop`. `CMD python servidor.py` (sin
  corchetes) arranca `/bin/sh -c "python servidor.py"`, el proceso 1 es
  `sh` y las señales se quedan en él. En la forma exec no hay shell, así
  que `$VARIABLE` no se expande.

### Ejemplo

Un script que imprime la fecha, la zona horaria, el usuario y la máquina donde
corre, en una tabla. Tres archivos en una carpeta vacía.

`fecha.py`:

```python
"""Imprime la fecha, el usuario y la máquina donde corre, en una tabla."""
import getpass
import os
import socket
from datetime import datetime

from tabulate import tabulate

ahora = datetime.now()
filas = [
    ["fecha", ahora.strftime("%Y-%m-%d")],
    ["hora", ahora.strftime("%H:%M:%S")],
    ["zona", os.environ.get("TZ", "sin definir")],
    ["usuario", getpass.getuser()],
    ["máquina", socket.gethostname()],
]
print(tabulate(filas, headers=["campo", "valor"]))
```

`requirements.txt`:

```
tabulate==0.9.0
```

`Dockerfile`:

```dockerfile
# Imagen base: Debian recortado con Python 3.11 ya instalado
FROM python:3.11-slim

# Directorio de trabajo dentro de la imagen; lo crea si no existe
WORKDIR /app

# Primero las dependencias: cambian poco y su capa se reutiliza
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código, que es lo que más cambia
COPY fecha.py .

# Variable de ambiente que el script lee en tiempo de ejecución
ENV TZ=America/Bogota

# Usuario sin privilegios; todo lo que sigue corre como él
RUN useradd --create-home --shell /bin/bash reloj
USER reloj

# Forma exec: python es el proceso 1 del contenedor
CMD ["python", "fecha.py"]
```

Construcción y tres ejecuciones: la normal, una que reemplaza el `CMD` y una
que sobreescribe el `ENV`:

```bash
docker build -t fecha .
docker run --rm fecha
docker run --rm fecha whoami
docker run --rm -e TZ=Europe/Madrid fecha
```

Salida de la construcción, recortada a los pasos:

```
[1/6] FROM docker.io/library/python:3.11-slim@sha256:a3ab0b96...
[2/6] WORKDIR /app
[3/6] COPY requirements.txt .
[4/6] RUN pip install --no-cache-dir -r requirements.txt
      Collecting tabulate==0.9.0 (from -r requirements.txt (line 1))
      Successfully installed tabulate-0.9.0
[5/6] COPY fecha.py .
[6/6] RUN useradd --create-home --shell /bin/bash reloj
naming to docker.io/library/fecha:latest done
```

Salida de las tres ejecuciones:

```
campo    valor
-------  --------------
fecha    2026-09-16
hora     14:29:17
zona     America/Bogota
usuario  reloj
máquina  8a5372a13dbb

reloj

campo    valor
-------  -------------
fecha    2026-09-16
hora     21:29:26
zona     Europe/Madrid
usuario  reloj
máquina  2db630ca6c58
```

El `whoami` reemplazó al `CMD` entero y confirmó el usuario; `-e TZ` cambió la
zona y la hora se movió siete horas. La misma imagen con `ENTRYPOINT` para ver
la diferencia. `Dockerfile.entrypoint`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fecha.py .
RUN useradd --create-home reloj
USER reloj
# ENTRYPOINT fija el programa; CMD son los argumentos por defecto
ENTRYPOINT ["python"]
CMD ["fecha.py"]
```

```bash
docker build -t fecha-entrypoint -f Dockerfile.entrypoint .
docker run --rm fecha-entrypoint | head -3
docker run --rm fecha-entrypoint -c 'import sys; print(sys.version)'
docker run --rm fecha-entrypoint whoami
```

```
campo    valor
-------  ------------
fecha    2026-09-16
3.11.15 (main, May 19 2026, 23:49:45) [GCC 14.2.0]
python: can't open file '/app/whoami': [Errno 2] No such file or directory
```

Con `ENTRYPOINT`, `-c '...'` se agregó a `python`, y `whoami` también: python
intentó abrir un archivo con ese nombre.

### Lo que suele fallar

- **`USER` antes del `pip install`.** Síntoma: durante la construcción pip
  dice `Defaulting to user installation because normal site-packages is not
  writeable` y `WARNING: The script gunicorn is installed in
  '/home/app/.local/bin' which is not on PATH`; al arrancar,
  `exec: "gunicorn": executable file not found in $PATH`. Causa: sin permiso
  sobre `site-packages`, pip instala en el home del usuario y los ejecutables
  quedan fuera del `PATH`. El `RUN` de pip va antes del `USER`.
- **Forma shell en el `CMD`.** `docker stop` tarda diez segundos y el
  contenedor termina con código 137. Medido con gunicorn:
  `CMD gunicorn --bind ...` tardó 11,3 s y salió con 137;
  `CMD ["gunicorn", "--bind", ...]` salió con 0. En la forma shell el proceso
  1 es `/bin/sh -c ...`, la señal SIGTERM se queda en él, y Docker mata el
  contenedor al vencer el plazo.
- **`$PORT` dentro de la forma exec.** Síntoma:
  `Error: '$PORT' is not a valid port number.` Causa: la lista JSON no pasa
  por un shell y la variable llega literal. O se escribe el número, o se usa
  `CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT ..."]`, donde el
  `exec` hace que gunicorn reemplace al shell como proceso 1.
- **Imagen base completa.** El flujo de Actions dice
  `la imagen pesa NNNN MB: revise la imagen base y lo que copia`, con un
  número por encima de 1500. `python:3.11` a secas pesa 1521 MB antes de
  copiar una sola línea; con la slim, la imagen del ejemplo quedó en 193 MB.
- **`apt-get` en varios `RUN` o sin limpieza.** Medido con `curl` y
  `procps`: todo en un `RUN` con `--no-install-recommends` y borrado de
  `/var/lib/apt/lists/*`, 196 MB; sin las dos cosas, 237 MB; con el
  `rm -rf` en un `RUN` aparte, 233 MB. Causa: cada `RUN` es una capa y
  borrar en una capa posterior no achica la anterior.

### Enlaces

- [Referencia del Dockerfile](https://docs.docker.com/reference/dockerfile/):
  todas las instrucciones con su sintaxis; `FROM`, `WORKDIR`, `COPY`,
  `RUN`, `ENV`, `EXPOSE`, `USER`, `CMD` y `ENTRYPOINT`, y la tabla de cómo
  se combinan `CMD` y `ENTRYPOINT`.
- [Buenas prácticas de construcción](https://docs.docker.com/build/building/best-practices/):
  el patrón de `apt-get` en un solo `RUN`, por qué usar la forma exec y
  cómo escoger la imagen base.
- [Imagen oficial de Python en Docker Hub](https://hub.docker.com/_/python):
  qué trae cada variante (`slim`, `alpine`, completa) y cuándo usar cada una.
- [`useradd` en Debian](https://manpages.debian.org/bookworm/passwd/useradd.8.en.html):
  las banderas `--create-home`, `--shell`, `--uid` y `--system`.
- [`adduser` en Debian](https://manpages.debian.org/bookworm/adduser/adduser.8.en.html):
  la alternativa con `--disabled-password` y `--gecos`.
- [`pip install`](https://pip.pypa.io/en/stable/cli/pip_install/):
  `-r`, `--no-cache-dir` y el resto de opciones de instalación.

## Parte 3: el .dockerignore

`docker build` empieza por mandarle al demonio todo lo que hay en la carpeta
del `Dockerfile`, el contexto de construcción, y `COPY . .` mete todo eso en
la imagen. El `.dockerignore` deja por fuera lo que no debe viajar: el entorno
virtual, la caché de Python, el historial de git y datos que no hacen parte
del servicio.

### Lo que se usa

- Un archivo llamado `.dockerignore` en la raíz del contexto, junto al
  `Dockerfile`. Uno dentro de una subcarpeta no se lee.
- Un patrón por línea, relativo a la raíz del contexto. `venv/` excluye la
  carpeta `venv` de la raíz; `*.bin`, los archivos `.bin` de la raíz.
- `**` casa cualquier cantidad de directorios: `**/__pycache__` excluye esa
  carpeta esté donde esté, y `**/*.pyc` los archivos compilados en cualquier
  nivel. Sin `**`, el patrón solo mira el primer nivel.
- `*` casa cualquier texto dentro de un nombre y `?` un solo carácter;
  `#` al inicio es un comentario.
- `!patrón` vuelve a incluir algo que una línea anterior excluyó; las líneas
  se aplican en orden.
- Excluir el propio `Dockerfile` y el `.dockerignore` es válido: la
  construcción los sigue usando, solo evita que `COPY . .` los meta en la
  imagen.

### Ejemplo

Una carpeta con un script que cuenta líneas, su archivo de muestra, y todo lo
que suele acumularse alrededor: un entorno virtual con Flask instalado, un
`__pycache__`, un `.git` y un archivo de datos de 60 MB.

```bash
mkdir contar && cd contar
cat > contar.py <<'FIN'
"""Cuenta las líneas de un archivo de texto que se pasa por argumento."""
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "muestra.txt"
with open(ruta, encoding="utf-8") as archivo:
    print(f"{ruta}: {sum(1 for _ in archivo)} líneas")
FIN
printf 'primera\nsegunda\ntercera\n' > muestra.txt
python3 -m venv venv && ./venv/bin/pip install -q flask==3.0.3
mkdir __pycache__ && dd if=/dev/urandom of=__pycache__/contar.cpython-311.pyc bs=1K count=8
git init -q . && git add contar.py muestra.txt && git commit -qm inicio
dd if=/dev/urandom of=datos_crudos.bin bs=1M count=60
cat > Dockerfile <<'FIN'
FROM python:3.11-slim
WORKDIR /app
COPY . .
CMD ["python", "contar.py"]
FIN
du -sh venv __pycache__ .git datos_crudos.bin
```

```
19M	venv
8,0K	__pycache__
116K	.git
60M	datos_crudos.bin
```

Primera construcción sin `.dockerignore`. Tres cosas para mirar: cuánto contexto
se transfiere, cuánto pesa la imagen y qué quedó adentro:

```bash
docker build -t contar . 2>&1 | grep 'transferring context'
docker image inspect contar --format 'imagen: {{.Size}} bytes'
docker run --rm contar ls -A /app
```

```
transferring context: 79.82MB 0.3s done
imagen: 338257090 bytes
.git Dockerfile __pycache__ contar.py datos_crudos.bin muestra.txt venv
```

Ahora con el `.dockerignore`:

```
# Todo lo que no debe entrar en la imagen
venv/
__pycache__/
*.pyc
.git/
*.bin
Dockerfile
.dockerignore
```

```bash
docker build -t contar . 2>&1 | grep 'transferring context'
docker image inspect contar --format 'imagen: {{.Size}} bytes'
docker run --rm contar ls -A /app
docker run --rm contar
```

```
transferring context: 350B done
imagen: 186263986 bytes
contar.py muestra.txt
muestra.txt: 3 líneas
```

De 79,82 MB de contexto a 350 B, y de 322 MB de imagen a 177 MB: la base más
el script, nada más.

### Lo que suele fallar

- **Confiar en el `.gitignore`.** El repositorio está limpio en GitHub, pero
  la imagen construida en la máquina propia pesa cientos de MB más que en
  Actions. `docker build` no lee `.gitignore`: el `venv/` local entra al
  contexto aunque git no lo vea. Son dos archivos distintos y los dos tienen
  que existir.
- **Patrón sin `**` para carpetas anidadas.** Síntoma: `__pycache__/` en el
  `.dockerignore` y aun así `app/__pycache__/` aparece dentro de la imagen.
  Causa: el patrón se ancla a la raíz del contexto. Probado:
  `__pycache__/` dejó pasar `./app/__pycache__/b.pyc`; `**/__pycache__` lo
  excluyó.
- **Un patrón que excluye de más.** Síntoma: la construcción se detiene con
  `failed to compute cache key: ... "/app/requirements.txt": not found`.
  Causa: un `**/*.txt` pensado para archivos de datos también tapó
  `requirements.txt`, y el `COPY` no lo encuentra en el contexto.
- **El archivo en la carpeta equivocada.** El flujo de Actions dice
  `Falta el archivo .dockerignore`, o la imagen sigue inflada. El archivo va
  en la raíz del repositorio, junto al `Dockerfile`, no dentro de `app/`.

### Enlaces

- [El contexto de construcción y el `.dockerignore`](https://docs.docker.com/build/concepts/context/):
  qué es el contexto, cómo se manda al demonio y la sintaxis completa del
  archivo de exclusiones, con ejemplos de `**` y `!`.
- [Referencia del Dockerfile](https://docs.docker.com/reference/dockerfile/):
  la sección sobre `.dockerignore` dentro de la referencia general.
- [`filepath.Match` de Go](https://pkg.go.dev/path/filepath):
  la sintaxis de patrones que Docker usa para casar los nombres.
- [`docker build`](https://docs.docker.com/reference/cli/docker/buildx/build/):
  las opciones `-t`, `-f`, `--no-cache` y cómo se indica el contexto.

## Parte 4: construir, correr y revisar el contenedor

Los comandos del README, que son los mismos que corre el flujo de Actions.

### Lo que se usa

- `docker build -t nombre[:etiqueta] ruta`: construye la imagen a partir del
  `Dockerfile` que está en `ruta` y la etiqueta con `nombre`. `.` es la
  carpeta actual. `-f otro.Dockerfile` cambia el archivo; `--no-cache`
  ignora la caché.
- `docker run --rm -d --name nombre -p host:contenedor imagen [comando]`:
  crea y arranca un contenedor. `-d` lo deja en segundo plano y devuelve su
  identificador; `--rm` lo borra cuando termina; `--name` le pone un nombre
  para referirse a él después; `-p 8000:8000` publica el puerto 8000 del
  contenedor en el 8000 de la máquina. Lo que va después de la imagen
  reemplaza al `CMD`.
- `docker ps [-a]`: lista los contenedores en ejecución; con `-a`, también
  los detenidos. Muestra el estado (`Up`, `Exited (código)`) y los puertos
  publicados.
- `docker logs nombre`: imprime lo que el proceso escribió en su salida
  estándar y de error. Es lo primero que se mira cuando un contenedor no
  responde. `-f` lo sigue en vivo.
- `docker exec nombre comando`: corre un comando adicional dentro de un
  contenedor que ya está andando, como el mismo usuario del `USER` del
  `Dockerfile`. `docker exec servicio whoami` es la prueba del ejercicio;
  `-it nombre bash` abre una terminal adentro.
- `docker image inspect imagen --format '{{.Size}}'`: saca un campo de los
  metadatos de la imagen con la sintaxis de plantillas de Go. `.Size` es el
  tamaño en bytes; `.Config.User`, `.Config.ExposedPorts` y `.Config.Cmd`
  muestran lo que dejaron `USER`, `EXPOSE` y `CMD`.
- `docker image ls [nombre]`: lista las imágenes locales con su tamaño. En
  Docker 29 las columnas son `DISK USAGE` y `CONTENT SIZE`; en versiones
  anteriores hay una sola, `SIZE`.
- `docker rm -f nombre`: detiene y borra el contenedor en un solo paso.
  `docker stop` solo lo detiene, con SIGTERM y diez segundos de gracia antes
  del SIGKILL.

### Ejemplo

Un servidor de archivos estáticos con el módulo `http.server` de la
biblioteca estándar, que corre como usuario sin privilegios. `curl` y `procps`
se instalan por `apt-get` para revisar el contenedor desde adentro. Dos archivos: `sitio/index.html` y el `Dockerfile`.

```bash
mkdir -p sitio
cat > sitio/index.html <<'FIN'
<!doctype html>
<title>Sitio de prueba</title>
<h1>Servido desde un contenedor</h1>
FIN
```

```dockerfile
FROM python:3.11-slim

# curl y ps sirven para revisar el contenedor desde adentro con docker exec.
# update e install van en el mismo RUN y la lista de paquetes se borra al final.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY sitio/ sitio/

RUN useradd --create-home web
USER web

# Documenta el puerto; la publicación real la hace docker run -p
EXPOSE 9000
CMD ["python", "-m", "http.server", "9000", "--bind", "0.0.0.0", "--directory", "sitio"]
```

La secuencia completa, en el orden del README:

```bash
docker build -t sitio .
docker run --rm -d --name web -p 9000:9000 sitio
curl http://localhost:9000/
docker ps --filter name=web
docker logs web
docker exec web whoami
docker exec web ps -o pid,user,args
docker exec web curl -sI localhost:9000/ | head -1
docker image inspect sitio --format '{{.Size}}'
docker image inspect sitio --format 'usuario={{.Config.User}} puertos={{.Config.ExposedPorts}}'
docker image ls sitio
docker rm -f web
```

Salida, recortada:

```
[2/5] RUN apt-get update && apt-get install -y --no-install-recommends curl procps && rm -rf /var/lib/apt/lists/*
      DONE 10.0s
[3/5] WORKDIR /srv
[4/5] COPY sitio/ sitio/
[5/5] RUN useradd --create-home web
82e952f4de06479e966f0956ddc1eac68caafb78c525619c13998dd106fcaee3
<!doctype html>
<title>Sitio de prueba</title>
<h1>Servido desde un contenedor</h1>
NAMES     IMAGE     STATUS         PORTS
web       sitio     Up 9 seconds   0.0.0.0:9000->9000/tcp, [::]:9000->9000/tcp
172.17.0.1 - - [16/Sep/2026 19:39:22] "GET / HTTP/1.1" 200 -
web
    PID USER     COMMAND
      1 web      python -m http.server 9000 --bind 0.0.0.0 --directory sitio
     15 web      ps -o pid,user,args
HTTP/1.0 200 OK
206491630
usuario=web puertos=map[9000/tcp:{}]
IMAGE          ID             DISK USAGE   CONTENT SIZE   EXTRA
sitio:latest   b1edd302a542        206MB           51MB   U
web
```

El proceso 1 es `python`, no `sh`, porque el `CMD` está en forma exec, y corre
como `web`. El tamaño en bytes se pasa a MB con aritmética del shell, igual
que en el flujo de Actions:

```bash
bytes=$(docker image inspect sitio --format '{{.Size}}')
echo "$((bytes / 1024 / 1024)) MB"
```

```
196 MB
```

El flujo de Actions no consulta el servicio una sola vez: lo intenta hasta
veinte veces con dos segundos de espera, porque el proceso tarda en arrancar.
La misma espera, en la máquina propia:

```bash
docker run --rm -d --name web -p 9000:9000 sitio
for i in $(seq 1 20); do
  curl -fsS http://localhost:9000/ >/dev/null 2>&1 && { echo "respondió en el intento $i"; break; }
  sleep 2
done
docker rm -f web
```

```
respondió en el intento 2
web
```

### Lo que suele fallar

- **Olvidar `-p`.** Síntoma: el contenedor está `Up`, `docker logs` muestra el
  servidor escuchando, y `curl` responde
  `curl: (7) Failed to connect to localhost:9000 after 0 ms: Could not connect to server`.
  Causa: `EXPOSE` documenta, no publica. El puerto solo se ve desde la
  máquina con `-p`.
- **Un `--rm` que borra la evidencia.** Síntoma: el `CMD` falla, el
  contenedor desaparece y `docker logs` dice
  `can not get logs from container which is dead or marked for removal`.
  Causa: `--rm` borra el contenedor en cuanto el proceso termina. Para
  depurar un arranque que falla se corre sin `--rm`; entonces
  `docker ps -a` muestra `Exited (2) 2 seconds ago` y `docker logs` el
  error, aquí `python: can't open file '/srv/noexiste.py'`.
- **Nombre repetido.**
  `Conflict. The container name "/web" is already in use by container "82e9..."`.
  El `docker rm -f` de la corrida anterior no se hizo, o el contenedor se
  corrió sin `--rm` y quedó detenido con ese nombre.
- **Puerto ocupado.** `Bind for 0.0.0.0:9000 failed: port is already
  allocated`: otro contenedor, o un proceso de la máquina, ya tiene ese
  puerto. `docker ps` muestra quién lo tiene; `ss -ltnp` si no es un
  contenedor.
- **Leer `docker image ls` en vez de `inspect`.** Síntoma: el número que se
  reporta no coincide con el del flujo de Actions. Causa: `image ls`
  redondea y en Docker 29 muestra dos columnas distintas; el flujo usa
  `inspect --format '{{.Size}}'` en bytes y lo divide por 1024 dos veces.

### Enlaces

- [`docker run`](https://docs.docker.com/reference/cli/docker/container/run/):
  `-d`, `--rm`, `--name`, `-p`, `-e` y el resto de opciones de arranque.
- [`docker exec`](https://docs.docker.com/reference/cli/docker/container/exec/):
  correr un comando en un contenedor que ya está andando, con `-it` para
  una terminal.
- [`docker logs`](https://docs.docker.com/reference/cli/docker/container/logs/):
  leer la salida del proceso, con `-f`, `--tail` y `--since`.
- [`docker image inspect`](https://docs.docker.com/reference/cli/docker/image/inspect/):
  los metadatos de una imagen y la opción `--format`.
- [Formato de salida con plantillas de Go](https://docs.docker.com/engine/cli/formatting/):
  la sintaxis `{{.Campo}}`, `{{json .}}` y las funciones disponibles en
  `--format`.
- [Publicar puertos](https://docs.docker.com/get-started/docker-concepts/running-containers/publishing-ports/):
  qué hace `-p host:contenedor` y en qué se diferencia de `EXPOSE`.

## Parte 5: capas y caché de construcción

Cada instrucción del `Dockerfile` produce una capa, y Docker reutiliza una capa
mientras la instrucción y todo lo que hay antes de ella no hayan cambiado. Para
`COPY`, cambiar el contenido de un archivo cambia la capa. A partir de la
primera capa que cambia, todas las que siguen se vuelven a construir.

### Lo que se usa

- `docker build` marca con `CACHED` cada paso que reutilizó. Construir dos
  veces seguidas sin cambios muestra todo en caché; cambiar un archivo
  muestra desde dónde se rehízo.
- `docker history imagen`: lista las capas de la imagen, de la más reciente a
  la base, con la instrucción que la creó y su tamaño.
  `--format 'table {{.CreatedBy}}\t{{.Size}}'` deja solo esas dos columnas;
  `--no-trunc` muestra las instrucciones completas.
- El orden que aprovecha la caché: lo que menos cambia arriba y lo que más
  cambia abajo. Base, dependencias del sistema, `requirements.txt` y su
  `pip install`, usuario, y al final el código.
- `docker build --no-cache`: rehace todo, para cuando se quiere medir el
  tiempo real o se sospecha de una capa vieja.

### Ejemplo

Con la imagen `fecha` de la sección del Dockerfile ya construida, una segunda
construcción sin tocar nada:

```bash
docker build -t fecha .
```

```
[2/6] WORKDIR /app
CACHED
[3/6] COPY requirements.txt .
CACHED
[4/6] RUN pip install --no-cache-dir -r requirements.txt
CACHED
[5/6] COPY fecha.py .
CACHED
[6/6] RUN useradd --create-home --shell /bin/bash reloj
CACHED
```

Un cambio en el código, cambiar la etiqueta `máquina` por `equipo` en
`fecha.py`, y otra construcción:

```bash
sed -i 's/"máquina"/"equipo"/' fecha.py
docker build -t fecha .
```

```
[2/6] WORKDIR /app
CACHED
[3/6] COPY requirements.txt .
CACHED
[4/6] RUN pip install --no-cache-dir -r requirements.txt
CACHED
[5/6] COPY fecha.py .
DONE 0.2s
[6/6] RUN useradd --create-home --shell /bin/bash reloj
DONE 0.6s
```

El `pip install` siguió en caché porque `requirements.txt` no cambió. El
`useradd` se volvió a correr porque está después del `COPY` del código; para
que también quede en caché, va antes. Ahora la versión que copia todo antes de
instalar, `Dockerfile.malorden`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
# Todo de una vez: cualquier cambio en el código invalida lo que sigue
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "fecha.py"]
```

```bash
docker build -t fecha-malorden -f Dockerfile.malorden .
sed -i 's/"equipo"/"máquina"/' fecha.py
docker build -t fecha-malorden -f Dockerfile.malorden .
```

Salida de la segunda construcción:

```
[2/4] WORKDIR /app
CACHED
[3/4] COPY . .
DONE 0.3s
[4/4] RUN pip install --no-cache-dir -r requirements.txt
DONE 2.6s
```

Un cambio de una palabra en el código reinstaló las dependencias. Con tabulate
son 2,6 s; con un `requirements.txt` real son minutos en cada construcción.
Las capas de la imagen buena, con `docker history`:

```bash
docker history fecha --format 'table {{.CreatedBy}}\t{{.Size}}'
```

```
CREATED BY                                      SIZE
CMD ["python" "fecha.py"]                       0B
USER reloj                                      0B
RUN /bin/sh -c useradd --create-home --shell…   69.6kB
ENV TZ=America/Bogota                           0B
COPY fecha.py . # buildkit                      12.3kB
RUN /bin/sh -c pip install --no-cache-dir -r…   12.8MB
COPY requirements.txt . # buildkit              12.3kB
WORKDIR /app                                    8.19kB
CMD ["python3"]                                 0B
RUN /bin/sh -c set -eux;  for src in idle3 p…   16.4kB
RUN /bin/sh -c set -eux;   savedAptMark="$(a…   48.4MB
ENV PYTHON_SHA256=272179ddd9a2e41a0fc8e42e33…   0B
ENV PYTHON_VERSION=3.11.15                      0B
ENV GPG_KEY=A035C8C19219BA821ECEA86B64E628F8…   0B
RUN /bin/sh -c set -eux;  apt-get update;  a…   4.95MB
ENV LANG=C.UTF-8                                0B
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr…   0B
# debian.sh --arch 'amd64' out/ 'trixie' '@1…   87.4MB
```

Las capas de arriba son las del `Dockerfile` propio; las de abajo, desde
`CMD ["python3"]`, vienen de `python:3.11-slim`. `CMD`, `USER` y `ENV` pesan
0 B porque solo cambian metadatos.

### Lo que suele fallar

- **Copiar el código antes de instalar.** Síntoma: cada construcción vuelve a
  descargar e instalar los paquetes aunque solo cambió una línea de Python.
  Causa: `COPY . .` o `COPY app/ app/` antes del `pip install` invalida esa
  capa con cualquier cambio en `app/`. Se copia `requirements.txt` solo,
  se instala, y después se copia el resto.
- **Borrar en una capa distinta de la que ensució.** Síntoma:
  `docker history` muestra la capa del `apt-get update` con 21,6 MB y la del
  `rm -rf` con 20,5 kB; la imagen no bajó. Causa: una capa nunca achica a
  las anteriores; el borrado va en el mismo `RUN`, encadenado con `&&`.
- **Cambiar el `requirements.txt` sin querer.** El `pip install` se rehace y
  no se sabe por qué. Para `COPY` cuenta el contenido, y un espacio al final
  o un cambio de fin de línea lo altera.
- **Fiarse de la caché al medir el tamaño.** Síntoma: se corrigió el
  `Dockerfile` y `docker image inspect` sigue dando el mismo número. Causa:
  la etiqueta apunta a la imagen nueva solo si la construcción se hizo;
  conviene confirmar con `docker image ls` que el `ID` cambió, o
  reconstruir con `--no-cache`.

### Enlaces

- [La caché de construcción](https://docs.docker.com/build/cache/):
  cómo Docker decide qué reutiliza y el orden de instrucciones que la
  aprovecha.
- [Invalidación de la caché](https://docs.docker.com/build/cache/invalidation/):
  qué cambios invalidan cada tipo de instrucción, con `COPY` y `RUN` en
  detalle.
- [Capas de una imagen](https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/):
  qué es una capa, cómo se apilan y por qué borrar en una capa posterior
  no reduce el tamaño.
- [`docker history`](https://docs.docker.com/reference/cli/docker/image/history/):
  las opciones `--format` y `--no-trunc` para leer las capas.
- [Controladores de almacenamiento](https://docs.docker.com/engine/storage/drivers/):
  cómo se guardan las capas en disco y qué es la capa de escritura del
  contenedor.

## Cómo compilar y ejecutar en la máquina propia

Solo hace falta Docker; `curl` viene en casi toda distribución y el flujo de
Actions lo usa igual.

### Debian y Ubuntu

El paquete de la distribución sirve para el ejercicio; el repositorio de
Docker trae la versión más reciente. Con el de la distribución:

```bash
sudo apt-get update
sudo apt-get install -y docker.io curl
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Hay que cerrar la sesión y volver a entrar para que el grupo `docker` aplique;
mientras tanto, los comandos piden `sudo`. La comprobación:

```bash
docker version --format 'cliente {{.Client.Version}} / servidor {{.Server.Version}}'
docker run --rm hello-world
```

Para instalar desde el repositorio de Docker, la guía de instalación enlazada
abajo tiene los pasos para cada versión de Debian y Ubuntu.

Los comandos del README corren tal cual. Si el puerto 8000 está ocupado en la
máquina, se cambia solo el lado izquierdo del `-p`: `-p 8080:8000` deja el
servicio en `http://localhost:8080` sin tocar la imagen.

### Windows con WSL2

Docker corre dentro de la distribución de Linux de WSL2, no en Windows. Dos
caminos:

- Docker Desktop para Windows con el motor de WSL2 activado. Se instala en
  Windows, y en la terminal de Ubuntu de WSL2 `docker` queda disponible
  después de habilitar la integración con esa distribución en la
  configuración de Docker Desktop.
- Docker Engine instalado dentro de la distribución, con los mismos pasos de
  Debian y Ubuntu de arriba. Si `systemctl` no está activo en esa
  distribución, el demonio se arranca con `sudo service docker start`.

En los dos casos el repositorio se clona dentro del sistema de archivos de
Linux, por ejemplo en `~/`, no en `/mnt/c/`: construir sobre `/mnt/c/` es
varias veces más lento y los permisos de los archivos se leen distinto.
`localhost:8000` funciona desde el navegador de Windows con las dos opciones.

### macOS

Docker Desktop para Mac trae el motor y la interfaz de línea de comandos; se
instala y los comandos del README corren en la terminal sin cambios. En los
equipos con procesador Apple Silicon la imagen que se construye es
`linux/arm64`, porque `python:3.11-slim` existe para esa arquitectura; el
flujo de Actions construye la suya en `linux/amd64` y no se cruzan. Para
reproducir de forma exacta lo que hace Actions, se construye para esa
plataforma:

```bash
docker build --platform linux/amd64 -t imagenes .
```

Es más lento porque emula el procesador, y solo hace falta cuando el
resultado difiere entre las dos.

### Enlaces

- [Instalar Docker Engine en Ubuntu](https://docs.docker.com/engine/install/ubuntu/):
  el repositorio oficial y los paquetes `docker-ce`, `docker-ce-cli` y
  `containerd.io`.
- [Instalar Docker Engine en Debian](https://docs.docker.com/engine/install/debian/):
  lo mismo para Debian.
- [Pasos después de instalar en Linux](https://docs.docker.com/engine/install/linux-postinstall/):
  el grupo `docker` para usar el comando sin `sudo` y el arranque
  automático del demonio.
- [Docker Desktop en Windows](https://docs.docker.com/desktop/setup/install/windows-install/):
  requisitos e instalación con el motor de WSL2.
- [Docker Desktop y WSL2](https://docs.docker.com/desktop/features/wsl/):
  la integración con cada distribución y dónde conviene guardar los
  archivos.
- [Instalar WSL](https://learn.microsoft.com/en-us/windows/wsl/install):
  `wsl --install` y cómo escoger la distribución.
- [Docker Desktop en macOS](https://docs.docker.com/desktop/setup/install/mac-install/):
  instalación para Apple Silicon y para Intel.
- [Construcción para varias plataformas](https://docs.docker.com/build/building/multi-platform/):
  la opción `--platform` y cómo funciona la emulación.
