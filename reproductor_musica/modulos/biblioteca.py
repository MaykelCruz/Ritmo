"""Biblioteca de canciones: una LISTA de diccionarios.

Cada canción: {"id": 1, "titulo": "...", "artista": "...", "genero": "...", "duracion": 212}
La duración se guarda en segundos.
"""
import unicodedata


def normalizar(texto):
    """Minúsculas y sin acentos, para buscar y ordenar sin que importen las tildes."""
    sin_acentos = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(letra for letra in sin_acentos if unicodedata.category(letra) != "Mn")


def siguiente_id(canciones):
    return max((c["id"] for c in canciones), default=0) + 1


def agregar(canciones, titulo, artista, genero, duracion):
    cancion = {
        "id": siguiente_id(canciones),
        "titulo": titulo.strip(),
        "artista": artista.strip(),
        "genero": genero.strip(),
        "duracion": int(duracion),
    }
    canciones.append(cancion)
    return cancion


def buscar_por_id(canciones, id_cancion):
    for cancion in canciones:
        if cancion["id"] == id_cancion:
            return cancion
    return None


def eliminar(canciones, id_cancion):
    cancion = buscar_por_id(canciones, id_cancion)
    if cancion is None:
        return False
    canciones.remove(cancion)
    return True


def filtrar(canciones, campo, texto):
    """Canciones cuyo 'campo' (artista, genero, titulo) contiene el texto."""
    buscado = normalizar(texto)
    return [c for c in canciones if buscado in normalizar(c[campo])]


def ordenar(canciones, campo):
    if campo == "duracion":
        return sorted(canciones, key=lambda c: c["duracion"])
    return sorted(canciones, key=lambda c: (normalizar(c[campo]), normalizar(c["titulo"])))


def formatear_duracion(segundos):
    horas, resto = divmod(segundos, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segs:02d}"
    return f"{minutos}:{segs:02d}"


def parsear_duracion(texto):
    """Acepta '3:45' o '225' (segundos). Devuelve segundos o None si no es válido."""
    texto = texto.strip()
    try:
        if ":" in texto:
            minutos, segundos = texto.split(":")
            if not 0 <= int(segundos) < 60:
                return None
            total = int(minutos) * 60 + int(segundos)
        else:
            total = int(texto)
    except ValueError:
        return None
    return total if total > 0 else None
