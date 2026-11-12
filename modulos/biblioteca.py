"""Biblioteca de canciones: una LISTA de diccionarios.

Cada canción:
    {"id": 1, "titulo": "...", "artista": "Shakira, Bad Bunny",
     "artistas": ["Shakira", "Bad Bunny"], "genero": "Pop", "duracion": 212}
- "artista" es el texto para mostrar; "artistas" es la lista ya separada (la usa el grafo).
- La duración se guarda en segundos.
Aquí también vive toda la validación de canciones.
"""
import re
import unicodedata

GENEROS = ["Rock", "Pop", "Salsa", "Folclor", "Reggaetón", "Cumbia", "Bachata", "Merengue",
           "Regional mexicano", "Balada", "Hip hop", "Electrónica", "Jazz", "Clásica", "Otro"]

LIMITE_TITULO = 100
LIMITE_ARTISTA = 60
MAX_ARTISTAS = 6
DURACION_MIN = 5                 # segundos
DURACION_MAX = 3 * 3600          # 3 horas
MAX_CANCIONES = 500

# Separadores entre artistas: coma, punto y coma, /, &, +  y las palabras y, x, con, feat, ft, with
SEPARADORES = re.compile(r"\s*[,;/&+]\s*|\s+(?:y|x|con|feat\.?|ft\.?|featuring|with)\s+", re.IGNORECASE)


# ---------------------------------------------------------------- texto
def normalizar(texto):
    """Minúsculas y sin acentos, para buscar y ordenar sin que importen las tildes."""
    sin_acentos = unicodedata.normalize("NFD", str(texto).strip().lower())
    return "".join(letra for letra in sin_acentos if unicodedata.category(letra) != "Mn")


def limpiar_texto(texto):
    """Quita espacios repetidos, saltos de línea y caracteres de control."""
    texto = unicodedata.normalize("NFC", str(texto))
    texto = re.sub(r"\s+", " ", texto)
    texto = "".join(letra for letra in texto if letra.isprintable())
    return texto.strip()


def tiene_contenido(texto):
    """True si el texto trae al menos una letra o un número (no solo símbolos)."""
    return any(letra.isalnum() for letra in texto)


def separar_artistas(texto):
    """'Shakira feat. Bad Bunny' -> ['Shakira', 'Bad Bunny']. Sin repetidos."""
    texto = re.sub(r"[()\[\]]", " ", limpiar_texto(texto))
    resultado, vistos = [], set()
    for parte in SEPARADORES.split(texto):
        parte = limpiar_texto(parte)
        if parte and normalizar(parte) not in vistos:
            vistos.add(normalizar(parte))
            resultado.append(parte)
    return resultado


def artistas_de(cancion):
    """Lista de artistas de una canción (también para canciones guardadas sin el campo)."""
    return cancion.get("artistas") or separar_artistas(cancion.get("artista", ""))


def normalizar_genero(texto):
    """Devuelve el género con su escritura oficial, 'Otro' si viene vacío, o None si no existe."""
    texto = limpiar_texto(texto)
    if not texto:
        return "Otro"
    for genero in GENEROS:
        if normalizar(genero) == normalizar(texto):
            return genero
    return None


# ---------------------------------------------------------------- duración
def formatear_duracion(segundos):
    horas, resto = divmod(segundos, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segs:02d}"
    return f"{minutos}:{segs:02d}"


def parsear_duracion(texto):
    """Acepta '3:45', '1:02:30' o '225' (segundos). Devuelve segundos o None si no es válido."""
    texto = str(texto).strip()
    if not re.fullmatch(r"\d{1,5}(:\d{1,2}){0,2}", texto):
        return None
    partes = [int(p) for p in texto.split(":")]
    if any(p > 59 for p in partes[1:]):
        return None
    total = 0
    for parte in partes:
        total = total * 60 + parte
    return total if total > 0 else None


# ---------------------------------------------------------------- consultas
def siguiente_id(canciones):
    return max((c["id"] for c in canciones), default=0) + 1


def buscar_por_id(canciones, id_cancion):
    for cancion in canciones:
        if cancion["id"] == id_cancion:
            return cancion
    return None


def buscar_duplicada(canciones, titulo, artistas, excluir_id=None):
    """Canción con el mismo título y los mismos artistas (sin importar orden, mayúsculas ni tildes)."""
    clave_titulo = normalizar(titulo)
    clave_artistas = {normalizar(a) for a in artistas}
    for cancion in canciones:
        if cancion["id"] == excluir_id:
            continue
        if normalizar(cancion["titulo"]) == clave_titulo and \
                {normalizar(a) for a in artistas_de(cancion)} == clave_artistas:
            return cancion
    return None


def filtrar(canciones, campo, texto):
    """Canciones cuyo 'campo' (artista, genero, titulo) contiene el texto."""
    buscado = normalizar(texto)
    return [c for c in canciones if buscado in normalizar(c[campo])]


def ordenar(canciones, campo):
    if campo == "duracion":
        return sorted(canciones, key=lambda c: c["duracion"])
    return sorted(canciones, key=lambda c: (normalizar(c[campo]), normalizar(c["titulo"])))


# ---------------------------------------------------------------- validación
def validar_cancion(canciones, titulo, artista, genero, duracion, excluir_id=None):
    """Valida los datos de una canción.

    Devuelve (errores, datos): 'errores' es {campo: mensaje} (vacío si todo está bien) y
    'datos' trae los valores ya limpios: titulo, artistas, artista, genero, duracion.
    """
    errores = {}

    titulo = limpiar_texto(titulo)
    if not titulo:
        errores["titulo"] = "Escribe el título de la canción."
    elif len(titulo) > LIMITE_TITULO:
        errores["titulo"] = f"El título es muy largo (máximo {LIMITE_TITULO} caracteres)."
    elif not tiene_contenido(titulo):
        errores["titulo"] = "El título debe tener letras o números."

    artistas = separar_artistas(artista)
    if not artistas:
        errores["artista"] = "Escribe al menos un artista."
    elif len(artistas) > MAX_ARTISTAS:
        errores["artista"] = f"Máximo {MAX_ARTISTAS} artistas por canción."
    else:
        for nombre in artistas:
            if len(nombre) > LIMITE_ARTISTA:
                errores["artista"] = f"«{nombre[:20]}…» es muy largo (máximo {LIMITE_ARTISTA} caracteres)."
                break
            if not tiene_contenido(nombre):
                errores["artista"] = f"«{nombre}» no parece un nombre de artista."
                break

    genero_ok = normalizar_genero(genero)
    if genero_ok is None:
        errores["genero"] = "Elige un género de la lista."

    segundos = parsear_duracion(duracion)
    if segundos is None:
        errores["duracion"] = "Usa el formato m:ss, por ejemplo 3:45."
    elif not DURACION_MIN <= segundos <= DURACION_MAX:
        errores["duracion"] = f"La duración debe estar entre {formatear_duracion(DURACION_MIN)} y {formatear_duracion(DURACION_MAX)}."

    if "titulo" not in errores and "artista" not in errores:
        existente = buscar_duplicada(canciones, titulo, artistas, excluir_id)
        if existente:
            errores["titulo"] = f"Ya existe «{existente['titulo']}» de {existente['artista']}."

    datos = {"titulo": titulo, "artistas": artistas, "artista": ", ".join(artistas),
             "genero": genero_ok, "duracion": segundos}
    return errores, datos


def agregar(canciones, datos):
    """Añade una canción ya validada (la salida de validar_cancion)."""
    cancion = {
        "id": siguiente_id(canciones),
        "titulo": datos["titulo"],
        "artista": datos["artista"],
        "artistas": list(datos["artistas"]),
        "genero": datos["genero"],
        "duracion": datos["duracion"],
    }
    canciones.append(cancion)
    return cancion


def actualizar(cancion, datos):
    """Reemplaza los datos de una canción con los de validar_cancion."""
    cancion["titulo"] = datos["titulo"]
    cancion["artista"] = datos["artista"]
    cancion["artistas"] = list(datos["artistas"])
    cancion["genero"] = datos["genero"]
    cancion["duracion"] = datos["duracion"]
    return cancion


def eliminar(canciones, id_cancion):
    cancion = buscar_por_id(canciones, id_cancion)
    if cancion is None:
        return False
    canciones.remove(cancion)
    return True


def reparar(canciones):
    """Revisa las canciones guardadas y corrige lo que se puede. Devuelve una lista de avisos.

    - Agrega la lista 'artistas' a las canciones que no la tienen.
    - Cambia a 'Otro' los géneros que no existen (o los escribe bien si solo cambia la tilde).
    - Avisa de duraciones raras y de canciones repetidas (no borra nada).
    """
    avisos = []
    for cancion in canciones:
        if not cancion.get("artistas"):
            cancion["artistas"] = separar_artistas(cancion.get("artista", "")) or ["Desconocido"]
        if not cancion.get("artista"):
            cancion["artista"] = ", ".join(cancion["artistas"])
        genero = normalizar_genero(cancion.get("genero", ""))
        if genero is None:
            avisos.append(f"«{cancion['titulo']}»: el género «{cancion['genero']}» no existe, ahora es «Otro».")
            genero = "Otro"
        cancion["genero"] = genero
        duracion = cancion.get("duracion")
        if not isinstance(duracion, int) or not DURACION_MIN <= duracion <= DURACION_MAX:
            avisos.append(f"«{cancion['titulo']}»: la duración ({duracion}) no es válida, revísala con Editar.")
    vistas = {}
    for cancion in canciones:
        clave = (normalizar(cancion["titulo"]), frozenset(normalizar(a) for a in cancion["artistas"]))
        if clave in vistas:
            avisos.append(f"«{cancion['titulo']}» está repetida (ids {vistas[clave]} y {cancion['id']}).")
        else:
            vistas[clave] = cancion["id"]
    return avisos