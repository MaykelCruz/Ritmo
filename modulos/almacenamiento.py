"""Lectura y escritura de archivos JSON (sin base de datos)."""
import json
import os

# La carpeta datos/ está al lado de main.py
CARPETA_DATOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos")


def ruta(nombre):
    return os.path.join(CARPETA_DATOS, nombre)


def cargar(nombre, por_defecto):
    """Devuelve el contenido del JSON, o 'por_defecto' si no existe o está dañado."""
    try:
        with open(ruta(nombre), "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def guardar(nombre, datos):
    """Escribe en un archivo temporal y luego lo cambia por el real, así un corte de luz o un
    error a mitad de la escritura no deja el JSON a medias."""
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    temporal = ruta(nombre) + ".tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta(nombre))