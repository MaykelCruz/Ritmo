"""Catálogo ordenado por título: ÁRBOL BINARIO DE BÚSQUEDA (BST).

Nodo: {"clave": titulo_normalizado, "ids": [ids con ese título], "izq": nodo | None, "der": nodo | None}

Por qué un árbol:
  - Buscar un título exacto o por prefijo ("la ...") no recorre toda la biblioteca.
  - El recorrido inorden entrega el catálogo ya ordenado de la A a la Z.
Es un índice: se reconstruye al abrir el programa a partir de la lista de canciones,
por eso no se guarda en JSON.
"""
from modulos.biblioteca import normalizar


def _insertar(raiz, clave, id_cancion):
    if raiz is None:
        return {"clave": clave, "ids": [id_cancion], "izq": None, "der": None}
    if clave == raiz["clave"]:
        if id_cancion not in raiz["ids"]:
            raiz["ids"].append(id_cancion)   # dos canciones con el mismo título
    elif clave < raiz["clave"]:
        raiz["izq"] = _insertar(raiz["izq"], clave, id_cancion)
    else:
        raiz["der"] = _insertar(raiz["der"], clave, id_cancion)
    return raiz


def insertar(raiz, titulo, id_cancion):
    return _insertar(raiz, normalizar(titulo), id_cancion)


def _buscar_nodo(raiz, clave):
    while raiz is not None:
        if clave == raiz["clave"]:
            return raiz
        raiz = raiz["izq"] if clave < raiz["clave"] else raiz["der"]
    return None


def buscar(raiz, titulo):
    """Ids de las canciones con ese título exacto (lista vacía si no hay)."""
    nodo = _buscar_nodo(raiz, normalizar(titulo))
    return list(nodo["ids"]) if nodo is not None else []


def _prefijo(nodo, prefijo, resultado):
    if nodo is None:
        return
    inicio = nodo["clave"][:len(prefijo)]
    if prefijo < inicio:                     # todo lo que empieza así está a la izquierda
        _prefijo(nodo["izq"], prefijo, resultado)
    elif prefijo > inicio:                   # ... o a la derecha
        _prefijo(nodo["der"], prefijo, resultado)
    else:                                    # este nodo coincide: puede haber más en ambos lados
        _prefijo(nodo["izq"], prefijo, resultado)
        resultado.extend(nodo["ids"])
        _prefijo(nodo["der"], prefijo, resultado)


def buscar_prefijo(raiz, prefijo):
    """Ids de las canciones cuyo título empieza con 'prefijo', en orden alfabético."""
    resultado = []
    _prefijo(raiz, normalizar(prefijo), resultado)
    return resultado


def inorden(raiz):
    """Ids de todas las canciones en orden alfabético de título (izquierda, nodo, derecha)."""
    if raiz is None:
        return []
    return inorden(raiz["izq"]) + raiz["ids"] + inorden(raiz["der"])


def altura(raiz):
    if raiz is None:
        return 0
    return 1 + max(altura(raiz["izq"]), altura(raiz["der"]))


def _minimo(nodo):
    while nodo["izq"] is not None:
        nodo = nodo["izq"]
    return nodo


def _quitar_nodo(raiz, clave):
    if raiz is None:
        return None
    if clave < raiz["clave"]:
        raiz["izq"] = _quitar_nodo(raiz["izq"], clave)
    elif clave > raiz["clave"]:
        raiz["der"] = _quitar_nodo(raiz["der"], clave)
    else:
        if raiz["izq"] is None:              # 0 o 1 hijo
            return raiz["der"]
        if raiz["der"] is None:
            return raiz["izq"]
        sucesor = _minimo(raiz["der"])       # 2 hijos: lo reemplaza el siguiente en orden
        raiz["clave"], raiz["ids"] = sucesor["clave"], sucesor["ids"]
        raiz["der"] = _quitar_nodo(raiz["der"], sucesor["clave"])
    return raiz


def eliminar(raiz, titulo, id_cancion):
    clave = normalizar(titulo)
    nodo = _buscar_nodo(raiz, clave)
    if nodo is None:
        return raiz
    if id_cancion in nodo["ids"]:
        nodo["ids"].remove(id_cancion)
    if nodo["ids"]:                          # todavía queda otra canción con ese título
        return raiz
    return _quitar_nodo(raiz, clave)


def _insertar_balanceado(raiz, ordenadas, inicio, fin):
    if inicio > fin:
        return raiz
    medio = (inicio + fin) // 2
    cancion = ordenadas[medio]
    raiz = insertar(raiz, cancion["titulo"], cancion["id"])
    raiz = _insertar_balanceado(raiz, ordenadas, inicio, medio - 1)
    return _insertar_balanceado(raiz, ordenadas, medio + 1, fin)


def construir(canciones):
    """Arma el árbol insertando siempre la canción del medio primero, para que quede balanceado.
    (Si se insertara en orden alfabético, el árbol se volvería una lista larga.)"""
    ordenadas = sorted(canciones, key=lambda c: normalizar(c["titulo"]))
    return _insertar_balanceado(None, ordenadas, 0, len(ordenadas) - 1)
