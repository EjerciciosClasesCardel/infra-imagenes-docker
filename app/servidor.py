"""Servicio mínimo de conteo de visitas. El código no se modifica."""
import os

from flask import Flask, jsonify

app = Flask(__name__)
VISITAS = {"total": 0}
SALUDO = os.environ.get("SALUDO", "Hola desde el contenedor")


@app.get("/")
def inicio():
    VISITAS["total"] += 1
    return jsonify(mensaje=SALUDO, visitas=VISITAS["total"])


@app.get("/health")
def salud():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
