"""Mapa de artistas relacionados: GRAFO NO DIRIGIDO con pesos.

Se guarda como diccionario de adyacencia (ya es JSON puro):
    {"Soda Stereo": {"Gustavo Cerati": 10, "Caifanes": 6}, ...}
El peso (1 a 10) dice qué tan parecidos son dos artistas.

Para qué sirve:
  - relacionados(): recomendaciones, recorrido por niveles (BFS) desde el artista que suena.
  - camino(): "¿cómo se conectan estos dos artistas?", camino más corto (BFS).
"""
from collections import deque


def agregar_artista(mapa, artista):
    mapa.setdefault(artista, {})


def conectar(mapa, artista_a, artista_b, peso):
    agregar_artista(mapa, artista_a)
    agregar_artista(mapa, artista_b)
    mapa[artista_a][artista_b] = peso
    mapa[artista_b][artista_a] = peso       # la relación va en los dos sentidos


def artistas_de(cancion):
    """Artistas de una canción (usa la lista 'artistas'; si falta, el texto completo)."""
    return cancion.get("artistas") or [cancion["artista"]]


def sincronizar(mapa, canciones):
    """Todo artista de la biblioteca debe existir como nodo, y quien colabora en una canción
    queda conectado con sus compañeros (sin tocar conexiones que ya existan)."""
    for cancion in canciones:
        for artista in artistas_de(cancion):
            agregar_artista(mapa, artista)
        conectar_colaboradores(mapa, artistas_de(cancion))


def conectar_colaboradores(mapa, artistas, peso=8):
    """Une a los artistas de una misma canción. No cambia el peso de una conexión existente."""
    for i, a in enumerate(artistas):
        for b in artistas[i + 1:]:
            if b not in mapa.get(a, {}):
                conectar(mapa, a, b, peso)


def quitar_artista(mapa, artista):
    """Borra un artista y todas sus conexiones."""
    for vecino in mapa.pop(artista, {}):
        mapa.get(vecino, {}).pop(artista, None)


def limpiar_sin_canciones(mapa, canciones):
    """Quita del mapa a los artistas que ya no tienen ninguna canción."""
    en_uso = {a for c in canciones for a in artistas_de(c)}
    for artista in [a for a in mapa if a not in en_uso]:
        quitar_artista(mapa, artista)


def relacionados(mapa, origen, profundidad=2):
    """Artistas alcanzables desde 'origen' hasta cierta cantidad de saltos.

    Recorrido por niveles: primero los vecinos directos (distancia 1), luego los vecinos de
    esos (distancia 2). La afinidad de un camino es la de su eslabón más débil.
    Devuelve [{"artista", "distancia", "afinidad"}] del más cercano y afín al menos.
    """
    if origen not in mapa:
        return []
    visitados = {origen}
    nivel = {origen: 10}
    resultado = []
    for distancia in range(1, profundidad + 1):
        siguiente = {}
        for artista, afinidad in nivel.items():
            for vecino, peso in mapa[artista].items():
                if vecino in visitados:
                    continue
                mejor = min(afinidad, peso)
                if mejor > siguiente.get(vecino, 0):
                    siguiente[vecino] = mejor
        for artista, afinidad in siguiente.items():
            visitados.add(artista)
            resultado.append({"artista": artista, "distancia": distancia, "afinidad": afinidad})
        nivel = siguiente
    resultado.sort(key=lambda r: (r["distancia"], -r["afinidad"], r["artista"]))
    return resultado


def relacionados_de_varios(mapa, origenes, profundidad=2):
    """Como relacionados(), pero partiendo de varios artistas (canciones con colaboraciones).
    Cada artista queda con su distancia más corta y su mejor afinidad; los de origen no salen."""
    mejores = {}
    for origen in origenes:
        for r in relacionados(mapa, origen, profundidad):
            if r["artista"] in origenes:
                continue
            actual = mejores.get(r["artista"])
            if actual is None or (r["distancia"], -r["afinidad"]) < (actual["distancia"], -actual["afinidad"]):
                mejores[r["artista"]] = r
    return sorted(mejores.values(), key=lambda r: (r["distancia"], -r["afinidad"], r["artista"]))


def camino(mapa, origen, destino):
    """Camino con menos saltos entre dos artistas, o None si no están conectados."""
    if origen not in mapa or destino not in mapa:
        return None
    padres = {origen: None}
    cola = deque([origen])
    while cola:
        actual = cola.popleft()
        if actual == destino:
            ruta = []
            while actual is not None:
                ruta.append(actual)
                actual = padres[actual]
            return ruta[::-1]
        for vecino in mapa[actual]:
            if vecino not in padres:
                padres[vecino] = actual
                cola.append(vecino)
    return None