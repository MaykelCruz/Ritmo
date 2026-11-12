"""Reproductor de música — servidor Flask.

Une los módulos (todos son funciones sobre listas y diccionarios, sin clases):
    biblioteca  -> LISTA de canciones
    playlist    -> LISTA DOBLEMENTE ENLAZADA (cola de reproducción)
    indice      -> ÁRBOL BINARIO DE BÚSQUEDA (catálogo por título)
    grafo       -> GRAFO de artistas relacionados
    historial   -> PILA de lo reproducido
    almacenamiento -> guardar/cargar JSON

Ejecutar:  python app.py   y abrir http://127.0.0.1:5000  (el reproductor está en /app)
El audio real sale de la carpeta musica/. Las canciones sin archivo se reproducen en modo
simulado (el tiempo avanza según la duración).
"""
import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from modulos import almacenamiento, biblioteca, grafo, historial, indice, playlist

app = Flask(__name__)

# Archivos de cada canción. Se reconocen por el nombre ("Título.mp3", "Artista - Título.mp3"
# o "<id>.mp3") y también se pueden adjuntar desde la biblioteca.
RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_AUDIO = os.path.join(RAIZ, "musica")
CARPETA_PORTADAS = os.path.join(RAIZ, "portadas")
EXT_AUDIO = (".mp3", ".ogg", ".wav", ".m4a")
EXT_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")


def buscar_archivo(carpeta, extensiones, cancion):
    """Nombre del archivo de esa carpeta que corresponde a la canción, o None."""
    if not os.path.isdir(carpeta):
        return None
    claves = {biblioteca.normalizar(cancion["titulo"]),
              biblioteca.normalizar(f'{cancion["artista"]} - {cancion["titulo"]}'),
              str(cancion["id"])}
    for nombre in sorted(os.listdir(carpeta)):
        base, extension = os.path.splitext(nombre)
        if extension.lower() in extensiones and biblioteca.normalizar(base) in claves:
            return nombre
    return None


def con_archivos(cancion):
    """Copia de la canción con las marcas 'audio' y 'portada' (no se guardan en el JSON)."""
    return {**cancion,
            "audio": buscar_archivo(CARPETA_AUDIO, EXT_AUDIO, cancion) is not None,
            "portada": buscar_archivo(CARPETA_PORTADAS, EXT_IMAGEN, cancion) is not None}


def guardar_archivo(carpeta, extensiones, id_cancion):
    """Guarda el archivo recibido como <id>.<ext>, reemplazando el anterior. Devuelve (ok, mensaje)."""
    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename:
        return False, "No se recibió ningún archivo"
    extension = os.path.splitext(archivo.filename)[1].lower()
    if extension not in extensiones:
        return False, "Formato no admitido. Usa " + ", ".join(e[1:] for e in extensiones)
    os.makedirs(carpeta, exist_ok=True)
    for nombre in os.listdir(carpeta):
        if os.path.splitext(nombre)[0] == str(id_cancion):
            os.remove(os.path.join(carpeta, nombre))
    archivo.save(os.path.join(carpeta, f"{id_cancion}{extension}"))
    return True, ""


# Todo el estado del programa vive en este diccionario (no hay objetos propios).
estado = {}


# ---------------------------------------------------------------- carga y guardado
def cargar_estado():
    canciones = almacenamiento.cargar("canciones.json", [])
    mapa = almacenamiento.cargar("grafo.json", {})
    datos_lista = almacenamiento.cargar("playlist.json", {"ids": [], "actual": None, "circular": False})
    pila = almacenamiento.cargar("historial.json", [])

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


def guardar_todo():
    almacenamiento.guardar("canciones.json", estado["canciones"])
    almacenamiento.guardar("grafo.json", estado["mapa"])
    almacenamiento.guardar("playlist.json", {
        "ids": playlist.a_lista(estado["lista"]),
        "actual": playlist.id_actual(estado["lista"]),
        "circular": estado["circular"],
    })
    almacenamiento.guardar("historial.json", estado["pila"])


def error(mensaje, codigo=400):
    return jsonify({"error": mensaje}), codigo


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
    """Canciones de artistas cercanos (en el grafo) al artista de la canción que suena."""
    id_actual = playlist.id_actual(estado["lista"])
    cancion = biblioteca.buscar_por_id(estado["canciones"], id_actual) if id_actual else None
    if cancion is None:
        return {"artista": None, "canciones": []}
    en_playlist = set(playlist.a_lista(estado["lista"]))
    salida = []
    for rel in grafo.relacionados(estado["mapa"], cancion["artista"], 2):
        for c in estado["canciones"]:
            if c["artista"] == rel["artista"]:
                salida.append({**c, "distancia": rel["distancia"], "afinidad": rel["afinidad"],
                               "en_playlist": c["id"] in en_playlist})
    return {"artista": cancion["artista"], "canciones": salida[:12]}


def construir_respuesta():
    lista = estado["lista"]
    mapa = estado["mapa"]
    return {
        "canciones": [con_archivos(c) for c in estado["canciones"]],
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


# ---------------------------------------------------------------- rutas
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


@app.get("/api/estado")
def ver_estado():
    return jsonify(construir_respuesta())


@app.get("/api/buscar")
def buscar():
    """Busca y ordena. El título usa el árbol (prefijo); lo demás recorre la lista."""
    q = request.args.get("q", "").strip()
    campo = request.args.get("campo", "titulo")
    orden = request.args.get("orden", "titulo")
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
    elif campo in ("artista", "genero"):
        resultado = biblioteca.filtrar(canciones, campo, q)
    else:
        return error("Campo de búsqueda no válido")

    if orden == "titulo":
        posicion = {i: n for n, i in enumerate(indice.inorden(estado["arbol"]))}
        resultado.sort(key=lambda c: posicion[c["id"]])
        if metodo == "lista":
            metodo = "árbol (inorden)"
    elif orden in ("artista", "genero", "duracion"):
        resultado = biblioteca.ordenar(resultado, orden)
    return jsonify({"resultados": [con_archivos(c) for c in resultado], "metodo": metodo})


@app.post("/api/canciones")
def crear_cancion():
    datos = request.get_json(silent=True) or {}
    titulo = str(datos.get("titulo", "")).strip()
    artista = str(datos.get("artista", "")).strip()
    genero = str(datos.get("genero", "")).strip() or "Otro"
    duracion = biblioteca.parsear_duracion(str(datos.get("duracion", "")))
    if not titulo or not artista:
        return error("Falta el título o el artista")
    if duracion is None:
        return error("Duración no válida (usa 3:45 o segundos)")
    cancion = biblioteca.agregar(estado["canciones"], titulo, artista, genero, duracion)
    estado["arbol"] = indice.insertar(estado["arbol"], cancion["titulo"], cancion["id"])
    grafo.agregar_artista(estado["mapa"], cancion["artista"])
    guardar_todo()
    return jsonify(cancion)


def servir(carpeta, extensiones, id_cancion):
    cancion = biblioteca.buscar_por_id(estado["canciones"], id_cancion)
    nombre = buscar_archivo(carpeta, extensiones, cancion) if cancion else None
    if nombre is None:
        return error("No hay archivo para esta canción", 404)
    return send_from_directory(carpeta, nombre, conditional=True)   # conditional permite adelantar la pista


@app.get("/audio/<int:id_cancion>")
def servir_audio(id_cancion):
    return servir(CARPETA_AUDIO, EXT_AUDIO, id_cancion)


@app.get("/portada/<int:id_cancion>")
def servir_portada(id_cancion):
    return servir(CARPETA_PORTADAS, EXT_IMAGEN, id_cancion)


def subir(carpeta, extensiones, id_cancion):
    if biblioteca.buscar_por_id(estado["canciones"], id_cancion) is None:
        return error("No existe esa canción", 404)
    ok, mensaje = guardar_archivo(carpeta, extensiones, id_cancion)
    return jsonify({"ok": True}) if ok else error(mensaje)


@app.post("/api/canciones/<int:id_cancion>/audio")
def subir_audio(id_cancion):
    return subir(CARPETA_AUDIO, EXT_AUDIO, id_cancion)


@app.post("/api/canciones/<int:id_cancion>/portada")
def subir_portada(id_cancion):
    return subir(CARPETA_PORTADAS, EXT_IMAGEN, id_cancion)


@app.delete("/api/canciones/<int:id_cancion>")
def borrar_cancion(id_cancion):
    cancion = biblioteca.buscar_por_id(estado["canciones"], id_cancion)
    if cancion is None:
        return error("No existe esa canción", 404)
    biblioteca.eliminar(estado["canciones"], id_cancion)
    estado["arbol"] = indice.eliminar(estado["arbol"], cancion["titulo"], id_cancion)
    playlist.eliminar(estado["lista"], id_cancion)
    historial.quitar(estado["pila"], id_cancion)
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/reproducir")
def ruta_reproducir():
    id_cancion = (request.get_json(silent=True) or {}).get("id")
    if biblioteca.buscar_por_id(estado["canciones"], id_cancion) is None:
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
    id_cancion = (request.get_json(silent=True) or {}).get("id")
    if biblioteca.buscar_por_id(estado["canciones"], id_cancion) is None:
        return error("No existe esa canción", 404)
    if not playlist.agregar_al_final(estado["lista"], id_cancion):
        return error("Ya está en la playlist")
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/continuacion")
def playlist_continuacion():
    id_cancion = (request.get_json(silent=True) or {}).get("id")
    if biblioteca.buscar_por_id(estado["canciones"], id_cancion) is None:
        return error("No existe esa canción", 404)
    if not playlist.a_continuacion(estado["lista"], id_cancion):
        return error("Esa ya es la que está sonando")
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/quitar")
def playlist_quitar():
    id_cancion = (request.get_json(silent=True) or {}).get("id")
    antes = playlist.id_actual(estado["lista"])
    if not playlist.eliminar(estado["lista"], id_cancion):
        return error("No está en la playlist", 404)
    despues = playlist.id_actual(estado["lista"])
    if despues is not None and despues != antes:      # sonaba esa: pasa a su vecina
        historial.apilar(estado["pila"], despues)
    guardar_todo()
    return jsonify({"ok": True})


@app.post("/api/playlist/mover")
def playlist_mover():
    datos = request.get_json(silent=True) or {}
    id_cancion, sentido = datos.get("id"), datos.get("sentido")
    ids = playlist.a_lista(estado["lista"])
    if id_cancion not in ids:
        return error("No está en la playlist", 404)
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
    datos = request.get_json(silent=True) or {}
    a, b = datos.get("a"), datos.get("b")
    try:
        peso = int(datos.get("peso"))
    except (TypeError, ValueError):
        return error("El peso debe ser un número del 1 al 10")
    if a not in estado["mapa"] or b not in estado["mapa"]:
        return error("Artista no encontrado")
    if a == b:
        return error("Elige dos artistas distintos")
    if not 1 <= peso <= 10:
        return error("El peso debe ser del 1 al 10")
    grafo.conectar(estado["mapa"], a, b, peso)
    guardar_todo()
    return jsonify({"ok": True})


@app.get("/api/camino")
def ruta_camino():
    ruta = grafo.camino(estado["mapa"], request.args.get("a", ""), request.args.get("b", ""))
    return jsonify({"camino": ruta})


cargar_estado()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
