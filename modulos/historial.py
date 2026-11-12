"""Historial de reproducción: PILA (el último en entrar es el primero en salir).

Es una lista de ids donde el final es el tope. Regla que mantiene el programa:
el tope es la canción que está sonando; debajo van las anteriores.
"""

LIMITE = 50      # máximo de canciones recordadas


def crear():
    return []


def esta_vacia(pila):
    return len(pila) == 0


def tope(pila):
    return pila[-1] if pila else None


def apilar(pila, id_cancion):
    if tope(pila) == id_cancion:             # no repetir la misma dos veces seguidas
        return
    pila.append(id_cancion)
    if len(pila) > LIMITE:
        del pila[0]                          # se olvida la más antigua


def desapilar(pila):
    return pila.pop() if pila else None


def ultimas(pila, cantidad):
    """Las últimas 'cantidad' canciones, de la más reciente a la más antigua."""
    return pila[::-1][:cantidad]


def quitar(pila, id_cancion):
    """Borra todas las apariciones de una canción (por ejemplo, si se elimina de la biblioteca)."""
    pila[:] = [i for i in pila if i != id_cancion]
