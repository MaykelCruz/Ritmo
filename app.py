"""Reproductor de música — servidor Flask.

Une los módulos (todos son funciones sobre listas y diccionarios, sin clases):
    biblioteca  -> LISTA de canciones (y toda la validación)
    playlist    -> LISTA DOBLEMENTE ENLAZADA (cola de reproducción)
    indice      -> ÁRBOL BINARIO DE BÚSQUEDA (catálogo por título)
    grafo       -> GRAFO de artistas relacionados
    historial   -> PILA de lo reproducido
    almacenamiento -> guardar/cargar JSON

Ejecutar:  python app.py   y abrir http://127.0.0.1:5000  (el reproductor está en /app)
El audio real sale de la carpeta musica/ y las portadas de portadas/.
Las canciones sin audio se reproducen en modo simulado.
"""
import os
import threading

from flask import Flask, g, jsonify, render_template, request, send_from_directory

from modulos import almacenamiento, biblioteca, grafo, historial, indice, playlist

app = Flask(__name__)

# ---------------------------------------------------------------- límites y carpetas
MB = 1024 * 1024
LIMITE_AUDIO = 30 * MB
LIMITE_PORTADA = 5 * MB
app.config["MAX_CONTENT_LENGTH"] = LIMITE_AUDIO + MB      # tope para cualquier petición
MAX_TEXTO_BUSQUEDA = 100
MAX_PLAYLIST = 500

# Archivos de cada canción. Se reconocen por el nombre ("<id>.mp3", "Título.mp3" o
# "Artista - Título.mp3") y también se pueden adjuntar desde la biblioteca.
RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_AUDIO = os.path.join(RAIZ, "musica")
CARPETA_PORTADAS = os.path.join(RAIZ, "portadas")
EXT_AUDIO = (".mp3", ".ogg", ".wav", ".m4a")
EXT_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")

# Todo el estado del programa vive en este diccionario (no hay objetos propios).
estado = {}

# Waitress atiende varias peticiones a la vez: este cerrojo hace que solo una modifique
# los datos al mismo tiempo (así no se corrompen las listas ni los JSON).
CERROJO = threading.RLock()


@app.before_request
def tomar_cerrojo():
    if request.method != "GET":
        CERROJO.acquire()
        g.con_cerrojo = True


@app.teardown_request
def soltar_cerrojo(_):
    if g.pop("con_cerrojo", False):
        CERROJO.release()


@app.after_request
def cabeceras_seguras(respuesta):
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["Referrer-Policy"] = "same-origin"
    return respuesta


# ---------------------------------------------------------------- utilidades de validación
def error(mensaje, codigo=400, campos=None):
    cuerpo_error = {"error": mensaje}
    if campos:
        cuerpo_error["campos"] = campos
    return jsonify(cuerpo_error), codigo


def cuerpo():
    """El JSON de la petición, siempre como diccionario (si viene otra cosa, uno vacío)."""
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


def entero(valor):
    """El valor si es un número entero de verdad (los booleanos y textos no cuentan)."""
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def cancion_o_404(id_cancion):
    return biblioteca.buscar_por_id(estado["canciones"], id_cancion)


def buscar_archivo(carpeta, extensiones, cancion):
    """Archivo de esa carpeta que corresponde a la canción, o None. El que se llama <id> manda."""
    if not os.path.isdir(carpeta):
        return None
    claves = {biblioteca.normalizar(cancion["titulo"]),
              biblioteca.normalizar(f'{cancion["artista"]} - {cancion["titulo"]}')}
    por_nombre = None
    for nombre in sorted(os.listdir(carpeta)):
        base, extension = os.path.splitext(nombre)
        if extension.lower() not in extensiones:
            continue
        if base == str(cancion["id"]):
            return nombre
        if por_nombre is None and biblioteca.normalizar(base) in claves:
            por_nombre = nombre
    return por_nombre


def con_archivos(cancion):
    """Copia de la canción con las marcas 'audio' y 'portada' (no se guardan en el JSON)."""
    return {**cancion,
            "audio": buscar_archivo(CARPETA_AUDIO, EXT_AUDIO, cancion) is not None,
            "portada": buscar_archivo(CARPETA_PORTADAS, EXT_IMAGEN, cancion) is not None}


def firma_valida(extension, cabecera):
    """Comprueba que el contenido del archivo sea del tipo que dice su extensión."""
    if extension == ".mp3":
        return cabecera[:3] == b"ID3" or (len(cabecera) > 1 and cabecera[0] == 0xFF and cabecera[1] & 0xE0 == 0xE0)
    if extension == ".ogg":
        return cabecera[:4] == b"OggS"
    if extension == ".wav":
        return cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WAVE"
    if extension == ".m4a":
        return cabecera[4:8] == b"ftyp"
    if extension in (".jpg", ".jpeg"):
        return cabecera[:3] == b"\xff\xd8\xff"
    if extension == ".png":
        return cabecera[:8] == b"\x89PNG\r\n\x1a\n"
    if extension == ".webp":
        return cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP"
    return False


def guardar_archivo(carpeta, extensiones, limite, id_cancion):
    """Valida y guarda el archivo recibido como <id>.<ext>. Devuelve (ok, mensaje)."""
    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename:
        return False, "No se recibió ningún archivo."
    extension = os.path.splitext(archivo.filename)[1].lower()
    if extension not in extensiones:
        return False, "Formato no admitido. Usa " + ", ".join(e[1:] for e in extensiones) + "."
    archivo.stream.seek(0, os.SEEK_END)
    tamano = archivo.stream.tell()
    archivo.stream.seek(0)
    if tamano == 0:
        return False, "El archivo está vacío."
    if tamano > limite:
        return False, f"El archivo pesa demasiado (máximo {limite // MB} MB)."
    if not firma_valida(extension, archivo.stream.read(16)):
        return False, f"El contenido no es un archivo {extension[1:]} válido."
    archivo.stream.seek(0)

    os.makedirs(carpeta, exist_ok=True)
    temporal = os.path.join(carpeta, f".subida-{id_cancion}.tmp")
    archivo.save(temporal)                                   # primero a un temporal
    for nombre in os.listdir(carpeta):                       # luego reemplaza el anterior
        if os.path.splitext(nombre)[0] == str(id_cancion) and nombre != os.path.basename(temporal):
            os.remove(os.path.join(carpeta, nombre))
    os.replace(temporal, os.path.join(carpeta, f"{id_cancion}{extension}"))
    return True, ""


# ---------------------------------------------------------------- carga y guardado
def cargar_estado():
    canciones = almacenamiento.cargar("canciones.json", [])
    if not isinstance(canciones, list):
        canciones = []
    mapa = almacenamiento.cargar("grafo.json", {})
    datos_lista = almacenamiento.cargar("playlist.json", {"ids": [], "actual": None, "circular": False})
    pila = almacenamiento.cargar("historial.json", [])

    for aviso in biblioteca.reparar(canciones):            # corrige lo que se puede y avisa en la consola
        print("[Ritmo] Aviso:", aviso)

    validos = {c["id"] for c in canciones}
    ids = [i for i in datos_lista["ids"] if i in validos]
    actual = datos_lista["actual"] if datos_lista["actual"] in validos else None

    grafo.sincronizar(mapa, canciones)
    estado["canciones"] = canciones
    estado["arbol"] = indice.construir(canciones)          # el índice no se guarda: se reconstruye
    estado["mapa"] = mapa
    estado["lista"] = playlist.desde_lista(ids, actual)    # igual: la cadena se reconstruye desde ids
    estado["circular"] = bool(datos_lista["circular"])
    estado["pila"] = [i for i in pila if i in validos]
    guardar_todo()


def guardar_todo():
    almacenamiento.guardar("canciones.json", estado["canciones"])
    almacenamiento.guardar("grafo.json", estado["mapa"])
    almacenamiento.guardar("playlist.json", {
        "ids": playlist.a_lista(estado["lista"]),
        "actual": playlist.id_actual(estado["lista"]),
        "circular": estado["circular"],
    })
    almacenamiento.guardar("historial.json", estado["pila"])


# ---------------------------------------------------------------- acciones de reproducción
def reproducir(id_cancion):
    """Pone a sonar una canción. Si no estaba en la playlist, entra justo después de la actual."""
    if playlist.buscar(estado["lista"], id_cancion) is None:
        playlist.a_continuacion(estado["lista"], id_cancion)
    playlist.ir_a(estado["lista"], id_cancion)
    historial.apilar(estado["pila"], id_cancion)


# ---------------------------------------------------------------- vistas de datos
def arbol_a_dict(nodo):
    if nodo is None:
        return None
    titulos = [biblioteca.buscar_por_id(estado["canciones"], i)["titulo"] for i in nodo["ids"]]
    return {"titulo": " / ".join(titulos), "ids": nodo["ids"],
            "izq": arbol_a_dict(nodo["izq"]), "der": arbol_a_dict(nodo["der"])}


def recomendaciones():
    """Canciones de artistas cercanos (en el grafo) a los artistas de la canción que suena."""
    id_actual = playlist.id_actual(estado["lista"])
    cancion = biblioteca.buscar_por_id(estado["canciones"], id_actual) if id_actual else None
    if cancion is None:
        return {"artista": None, "artistas": [], "canciones": []}
    artistas = biblioteca.artistas_de(cancion)
    en_playlist = set(playlist.a_lista(estado["lista"]))
    salida = []
    for rel in grafo.relacionados_de_varios(estado["mapa"], artistas, 2):
        for c in estado["canciones"]:
            if rel["artista"] in biblioteca.artistas_de(c) and c["id"] != cancion["id"]:
                salida.append({**con_archivos(c), "distancia": rel["distancia"], "afinidad": rel["afinidad"],
                               "en_playlist": c["id"] in en_playlist})
    vistas, unicas = set(), []                              # una canción con dos artistas cercanos sale una vez
    for c in salida:
        if c["id"] not in vistas:
            vistas.add(c["id"])
            unicas.append(c)
    nombres = artistas[0] if len(artistas) == 1 else ", ".join(artistas[:-1]) + " y " + artistas[-1]
    return {"artista": nombres, "artistas": artistas, "canciones": unicas[:12]}


def construir_respuesta():
    lista = estado["lista"]
    mapa = estado["mapa"]
    return {
        "canciones": [con_archivos(c) for c in estado["canciones"]],
        "generos": biblioteca.GENEROS,
        "limites": {
            "titulo": biblioteca.LIMITE_TITULO, "artista": biblioteca.LIMITE_ARTISTA,
            "max_artistas": biblioteca.MAX_ARTISTAS, "audio_mb": LIMITE_AUDIO // MB,
            "portada_mb": LIMITE_PORTADA // MB,
        },
        "playlist": {
            "ids": playlist.a_lista(lista),
            "actual": playlist.id_actual(lista),
            "posicion": playlist.posicion_actual(lista),
            "circular": estado["circular"],
        },
        "historial": historial.ultimas(estado["pila"], 10),
        "recomendaciones": recomendaciones(),
        "arbol": arbol_a_dict(estado["arbol"]),
        "grafo": mapa,
        "stats": {
            "canciones": len(estado["canciones"]),
            "artistas": len(mapa),
            "conexiones": sum(len(v) for v in mapa.values()) // 2,
            "altura_arbol": indice.altura(estado["arbol"]),
            "en_playlist": lista["tamanio"],
            "en_historial": len(estado["pila"]),
        },
    }


# ---------------------------------------------------------------- páginas
@app.get("/")
def presentacion():
    return render_template("landing.html")


@app.get("/app")
def reproductor():
    return render_template("index.html")


@app.errorhandler(404)
def no_encontrada(_):
    if request.path.startswith(("/api/", "/audio/", "/portada/")):
        return error("No encontrado", 404)
    return render_template("404.html"), 404


@app.errorhandler(413)
def demasiado_grande(_):
    return error(f"El archivo pesa demasiado (máximo {LIMITE_AUDIO // MB} MB).", 413)


@app.errorhandler(405)
def metodo_no_permitido(_):
    return error("Método no permitido", 405)


# ---------------------------------------------------------------- API de lectura
@app.get("/api/estado")
def ver_estado():
    return jsonify(construir_respuesta())


@app.get("/api/buscar")
def buscar():
    """Busca y ordena. El título usa el árbol (prefijo); lo demás recorre la lista."""
    q = biblioteca.limpiar_texto(request.args.get("q", ""))[:MAX_TEXTO_BUSQUEDA]
    campo = request.args.get("campo", "titulo")
    orden = request.args.get("orden", "titulo")
    if campo not in ("titulo", "artista", "genero"):
        return error("Campo de búsqueda no válido")
    if orden not in ("titulo", "artista", "genero", "duracion"):
        return error("Orden no válido")
    canciones = estado["canciones"]
    metodo = "lista"

    if not q:
        resultado = list(canciones)
    elif campo == "titulo":
        ids = indice.buscar_prefijo(estado["arbol"], q)
        if ids:
            resultado = [biblioteca.buscar_por_id(canciones, i) for i in ids]
            metodo = "árbol (prefijo)"
        else:
            resultado = biblioteca.filtrar(canciones, "titulo", q)
    else:
        resultado = biblioteca.filtrar(canciones, campo, q)

    if orden == "titulo":
        posicion = {i: n for n, i in enumerate(indice.inorden(estado["arbol"]))}
        resultado.sort(key=lambda c: posicion[c["id"]])
        if metodo == "lista":
            metodo = "árbol (inorden)"
    else:
        resultado = biblioteca.ordenar(resultado, orden)
    return jsonify({"resultados": [con_archivos(c) for c in resultado], "metodo": metodo})


@app.get("/audio/<int:id_cancion>")
def servir_audio(id_cancion):
    return servir(CARPETA_AUDIO, EXT_AUDIO, id_cancion)


@app.get("/portada/<int:id_cancion>")
def servir_portada(id_cancion):
    return servir(CARPETA_PORTADAS, EXT_IMAGEN, id_cancion)


def servir(carpeta, extensiones, id_cancion):
    cancion = cancion_o_404(id_cancion)
    nombre = buscar_archivo(carpeta, extensiones, cancion) if cancion else None
    if nombre is None:
        return error("No hay archivo para esta canción", 404)
    return send_from_directory(carpeta, nombre, conditional=True)   # conditional permite adelantar la pista


@app.get("/api/camino")
def ruta_camino():
    origen, destino = request.args.get("a", ""), request.args.get("b", "")
    if origen not in estado["mapa"] or destino not in estado["mapa"]:
        return error("Elige dos artistas de la lista")
    return jsonify({"camino": grafo.camino(estado["mapa"], origen, destino)})


# ---------------------------------------------------------------- API de canciones
@app.post("/api/validar")
def validar():
    """Valida los datos de una canción sin guardar nada (el formulario lo usa mientras escribes)."""
    datos = cuerpo()
    excluir = entero(datos.get("excluir_id"))
    errores, limpio = biblioteca.validar_cancion(
        estado["canciones"], datos.get("titulo", ""), datos.get("artista", ""),
        datos.get("genero", ""), datos.get("duracion", ""), excluir)
    return jsonify({"ok": not errores, "errores": errores, "artistas": limpio["artistas"]})


@app.post("/api/canciones")
def crear_cancion():
    datos = cuerpo()
    if len(estado["canciones"]) >= biblioteca.MAX_CANCIONES:
        return error(f"La biblioteca está llena (máximo {biblioteca.MAX_CANCIONES} canciones).")
    errores, limpio = biblioteca.validar_cancion(
        estado["canciones"], datos.get("titulo", ""), datos.get("artista", ""),
        datos.get("genero", ""), datos.get("duracion", ""))
    if errores:
        return error("Revisa los campos marcados.", 400, errores)
    cancion = biblioteca.agregar(estado["canciones"], limpio)
    estado["arbol"] = indice.insertar(estado["arbol"], cancion["titulo"], cancion["id"])
    grafo.sincronizar(estado["mapa"], [cancion])          # crea los artistas y conecta a los colaboradores
    guardar_todo()
    return jsonify(cancion)


@app.put("/api/canciones/<int:id_cancion>")
def editar_cancion(id_cancion):
    cancion = cancion_o_404(id_cancion)
    if cancion is None:
        return error("No existe esa canción", 404)
    datos = cuerpo()
    errores, limpio = biblioteca.validar_cancion(
        estado["canciones"], datos.get("titulo", ""), datos.get("artista", ""),
        datos.get("genero", ""), datos.get("duracion", ""), excluir_id=id_cancion)
    if errores:
        return error("Revisa los campos marcados.", 400, errores)
    estado["arbol"] = indice.eliminar(estado["arbol"], cancion["titulo"], id_cancion)
    biblioteca.actualizar(cancion, limpio)
    estado["arbol"] = indice.insertar(estado["arbol"], cancion["titulo"], id_cancion)
    grafo.sincronizar(estado["mapa"], [cancion])
    grafo.limpiar_sin_canciones(estado["mapa"], estado["canciones"])   # por si cambió de artista
    guardar_todo()
    return jsonify(cancion)


@app.delete("/api/canciones/<int:id_cancion>")
def borrar_cancion(id_cancion):
    cancion = cancion_o_404(id_cancion)
    if cancion is None:
        return error("No existe esa canción", 404)
    biblioteca.eliminar(estado["canciones"], id_cancion)
    estado["arbol"] = indice.eliminar(estado["arbol"], cancion["titulo"], id_cancion)
    antes = playlist.id_actual(estado["lista"])
    playlist.eliminar(estado["lista"], id_cancion)
    despues = playlist.id_actual(estado["lista"])
    historial.quitar(estado["pila"], id_cancion)
    if despues is not None and despues != antes:
        historial.apilar(estado["pila"], despues)
    grafo.limpiar_sin_canciones(estado["mapa"], estado["canciones"])
    borrar_archivos_subidos(id_cancion)
    guardar_todo()
    return jsonify({"ok": True})


def borrar_archivos_subidos(id_cancion):
    """Quita el audio y la portada subidos para esa canción (los que se llaman <id>.ext).
    Si no, el id se reutiliza y la canción nueva heredaría los archivos de la borrada.
    Los archivos con nombre propio (Título.mp3) no se tocan."""
    for carpeta in (CARPETA_AUDIO, CARPETA_PORTADAS):
        if os.path.isdir(carpeta):
            for nombre in os.listdir(carpeta):
                if os.path.splitext(nombre)[0] == str(id_cancion):
                    os.remove(os.path.join(carpeta, nombre))


def subir(carpeta, extensiones, limite, id_cancion):
    if cancion_o_404(id_cancion) is None:
        return error("No existe esa canción", 404)
    ok, mensaje = guardar_archivo(carpeta, extensiones, limite, id_cancion)
    return jsonify({"ok": True}) if ok else error(mensaje)


@app.post("/api/canciones/<int:id_cancion>/audio")
def subir_audio(id_cancion):
    return subir(CARPETA_AUDIO, EXT_AUDIO, LIMITE_AUDIO, id_cancion)


@app.post("/api/canciones/<int:id_cancion>/portada")
def subir_portada(id_cancion):
    return subir(CARPETA_PORTADAS, EXT_IMAGEN, LIMITE_PORTADA, id_cancion)


# ---------------------------------------------------------------- API de reproducción
@app.post("/api/reproducir")
def ruta_reproducir():
    id_cancion = entero(cuerpo().get("id"))
    if cancion_o_404(id_cancion) is None:
        return error("No existe esa canción", 404)
    reproducir(id_cancion)
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/siguiente")
def ruta_siguiente():
    nuevo = playlist.avanzar(estado["lista"], estado["circular"])
    if nuevo is not None:
        historial.apilar(estado["pila"], nuevo)
    guardar_todo()
    return jsonify({"cambio": nuevo is not None})


@app.post("/api/anterior")
def ruta_anterior():
    nuevo = playlist.retroceder(estado["lista"], estado["circular"])
    if nuevo is not None:
        historial.apilar(estado["pila"], nuevo)
    guardar_todo()
    return jsonify({"cambio": nuevo is not None})


@app.post("/api/volver")
def ruta_volver():
    """Deshace la última reproducción: saca el tope de la pila y suena la que estaba debajo."""
    if len(estado["pila"]) < 2:
        return error("No hay una canción anterior en el historial")
    historial.desapilar(estado["pila"])
    reproducir(historial.tope(estado["pila"]))
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/agregar")
def playlist_agregar():
    id_cancion = entero(cuerpo().get("id"))
    if cancion_o_404(id_cancion) is None:
        return error("No existe esa canción", 404)
    if estado["lista"]["tamanio"] >= MAX_PLAYLIST:
        return error(f"La cola está llena (máximo {MAX_PLAYLIST} canciones).")
    if not playlist.agregar_al_final(estado["lista"], id_cancion):
        return error("Ya está en la cola.")
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/continuacion")
def playlist_continuacion():
    id_cancion = entero(cuerpo().get("id"))
    if cancion_o_404(id_cancion) is None:
        return error("No existe esa canción", 404)
    if not playlist.a_continuacion(estado["lista"], id_cancion):
        return error("Esa ya es la que está sonando.")
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/quitar")
def playlist_quitar():
    id_cancion = entero(cuerpo().get("id"))
    antes = playlist.id_actual(estado["lista"])
    if not playlist.eliminar(estado["lista"], id_cancion):
        return error("No está en la cola.", 404)
    despues = playlist.id_actual(estado["lista"])
    if despues is not None and despues != antes:      # sonaba esa: pasa a su vecina
        historial.apilar(estado["pila"], despues)
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/mover")
def playlist_mover():
    datos = cuerpo()
    id_cancion, sentido = entero(datos.get("id")), datos.get("sentido")
    if sentido not in ("subir", "bajar"):
        return error("Sentido no válido")
    ids = playlist.a_lista(estado["lista"])
    if id_cancion not in ids:
        return error("No está en la cola.", 404)
    posicion = ids.index(id_cancion)
    if sentido == "subir" and posicion > 0:
        if posicion == 1:
            playlist.mover_al_inicio(estado["lista"], id_cancion)
        else:
            playlist.mover_despues(estado["lista"], id_cancion, ids[posicion - 2])
    elif sentido == "bajar" and posicion < len(ids) - 1:
        playlist.mover_despues(estado["lista"], id_cancion, ids[posicion + 1])
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/mezclar")
def playlist_mezclar():
    playlist.mezclar(estado["lista"])
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/circular")
def playlist_circular():
    estado["circular"] = not estado["circular"]
    guardar_todo()
    return jsonify({"circular": estado["circular"]})


@app.post("/api/grafo/conectar")
def grafo_conectar():
    datos = cuerpo()
    a, b = datos.get("a"), datos.get("b")
    peso = entero(datos.get("peso"))
    if a not in estado["mapa"] or b not in estado["mapa"]:
        return error("Artista no encontrado")
    if a == b:
        return error("Elige dos artistas distintos")
    if peso is None or not 1 <= peso <= 10:
        return error("El peso debe ser un número del 1 al 10")
    grafo.conectar(estado["mapa"], a, b, peso)
    guardar_todo()
    return jsonify({"ok": True})


cargar_estado()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )