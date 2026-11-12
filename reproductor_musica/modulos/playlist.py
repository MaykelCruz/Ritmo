"""Playlist como LISTA DOBLEMENTE ENLAZADA.

Cada nodo es un diccionario: {"id": id_cancion, "anterior": nodo | None, "siguiente": nodo | None}
La lista es otro diccionario: {"cabeza": nodo, "cola": nodo, "actual": nodo, "tamanio": n}

Por qué una lista enlazada y no una lista normal:
  - "Reproducir a continuación" inserta una canción justo después de la actual.
  - Quitar o mover canciones en medio no obliga a desplazar todo lo demás.
  - Siguiente / anterior son seguir un enlace.

Los nodos se apuntan entre sí (hay ciclos), y json no puede guardar ciclos. Por eso en el
archivo se guarda solo la lista de ids (a_lista) y al cargar se reconstruye (desde_lista).
"""
import random


def crear():
    return {"cabeza": None, "cola": None, "actual": None, "tamanio": 0}


def _nuevo_nodo(id_cancion):
    return {"id": id_cancion, "anterior": None, "siguiente": None}


def buscar(lista, id_cancion):
    nodo = lista["cabeza"]
    while nodo is not None:
        if nodo["id"] == id_cancion:
            return nodo
        nodo = nodo["siguiente"]
    return None


def _enlazar_despues(lista, referencia, nodo):
    """Pone 'nodo' justo después de 'referencia'. Si referencia es None, lo pone al inicio."""
    if referencia is None:
        nodo["anterior"] = None
        nodo["siguiente"] = lista["cabeza"]
        if lista["cabeza"] is not None:
            lista["cabeza"]["anterior"] = nodo
        else:
            lista["cola"] = nodo
        lista["cabeza"] = nodo
    else:
        nodo["anterior"] = referencia
        nodo["siguiente"] = referencia["siguiente"]
        if referencia["siguiente"] is not None:
            referencia["siguiente"]["anterior"] = nodo
        else:
            lista["cola"] = nodo
        referencia["siguiente"] = nodo


def _desenlazar(lista, nodo):
    """Saca el nodo de la cadena (los vecinos se conectan entre sí)."""
    anterior, siguiente = nodo["anterior"], nodo["siguiente"]
    if anterior is not None:
        anterior["siguiente"] = siguiente
    else:
        lista["cabeza"] = siguiente
    if siguiente is not None:
        siguiente["anterior"] = anterior
    else:
        lista["cola"] = anterior
    nodo["anterior"] = None
    nodo["siguiente"] = None


def agregar_al_final(lista, id_cancion):
    if buscar(lista, id_cancion) is not None:
        return False                      # no se permiten repetidas
    nodo = _nuevo_nodo(id_cancion)
    _enlazar_despues(lista, lista["cola"], nodo)
    lista["tamanio"] += 1
    if lista["actual"] is None:
        lista["actual"] = nodo
    return True


def a_continuacion(lista, id_cancion):
    """'Reproducir a continuación': la deja justo después de la actual (la mueve si ya estaba)."""
    actual = lista["actual"]
    if actual is None:
        return agregar_al_final(lista, id_cancion)
    nodo = buscar(lista, id_cancion)
    if nodo is actual:
        return False
    if nodo is None:
        nodo = _nuevo_nodo(id_cancion)
        lista["tamanio"] += 1
    else:
        _desenlazar(lista, nodo)
    _enlazar_despues(lista, actual, nodo)
    return True


def eliminar(lista, id_cancion):
    nodo = buscar(lista, id_cancion)
    if nodo is None:
        return False
    if lista["actual"] is nodo:           # si era la que sonaba, pasa a la vecina
        lista["actual"] = nodo["siguiente"] if nodo["siguiente"] is not None else nodo["anterior"]
    _desenlazar(lista, nodo)
    lista["tamanio"] -= 1
    return True


def mover_despues(lista, id_cancion, id_referencia):
    nodo = buscar(lista, id_cancion)
    referencia = buscar(lista, id_referencia)
    if nodo is None or referencia is None or nodo is referencia:
        return False
    if referencia["siguiente"] is not nodo:
        _desenlazar(lista, nodo)
        _enlazar_despues(lista, referencia, nodo)
    return True


def mover_al_inicio(lista, id_cancion):
    nodo = buscar(lista, id_cancion)
    if nodo is None:
        return False
    if lista["cabeza"] is not nodo:
        _desenlazar(lista, nodo)
        _enlazar_despues(lista, None, nodo)
    return True


def avanzar(lista, circular=False):
    """Pasa a la siguiente. Devuelve su id, o None si ya era la última (y no es circular)."""
    actual = lista["actual"]
    if actual is None:
        return None
    if actual["siguiente"] is not None:
        lista["actual"] = actual["siguiente"]
    elif circular:
        lista["actual"] = lista["cabeza"]
    else:
        return None
    return lista["actual"]["id"]


def retroceder(lista, circular=False):
    actual = lista["actual"]
    if actual is None:
        return None
    if actual["anterior"] is not None:
        lista["actual"] = actual["anterior"]
    elif circular:
        lista["actual"] = lista["cola"]
    else:
        return None
    return lista["actual"]["id"]


def ir_a(lista, id_cancion):
    nodo = buscar(lista, id_cancion)
    if nodo is None:
        return False
    lista["actual"] = nodo
    return True


def id_actual(lista):
    return lista["actual"]["id"] if lista["actual"] is not None else None


def posicion_actual(lista):
    """Posición (empezando en 1) de la canción actual; 0 si la lista está vacía."""
    posicion = 0
    nodo = lista["cabeza"]
    while nodo is not None:
        posicion += 1
        if nodo is lista["actual"]:
            return posicion
        nodo = nodo["siguiente"]
    return 0


def a_lista(lista):
    """Recorre la cadena y devuelve los ids en orden (esto es lo que se guarda en JSON)."""
    ids = []
    nodo = lista["cabeza"]
    while nodo is not None:
        ids.append(nodo["id"])
        nodo = nodo["siguiente"]
    return ids


def desde_lista(ids, id_en_curso=None):
    """Reconstruye la cadena de nodos a partir de una lista de ids."""
    lista = crear()
    for id_cancion in ids:
        agregar_al_final(lista, id_cancion)
    if id_en_curso is not None:
        ir_a(lista, id_en_curso)
    return lista


def mezclar(lista):
    """Desordena la playlist; la canción que suena queda de primera."""
    ids = a_lista(lista)
    en_curso = id_actual(lista)
    random.shuffle(ids)
    if en_curso in ids:
        ids.remove(en_curso)
        ids.insert(0, en_curso)
    lista.update(desde_lista(ids, en_curso))
