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


def sincronizar(mapa, canciones):
    """Todo artista de la biblioteca debe existir como nodo (aunque no tenga conexiones)."""
    for cancion in canciones:
        agregar_artista(mapa, cancion["artista"])


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
