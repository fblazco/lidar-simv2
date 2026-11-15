"""Evasión aprendida: no se agrega ninguna capa.

El propio algoritmo de navegación se ocupa de los obstáculos con lo que percibe
del LiDAR (la red y la tabla de reglas lo aprenden al entrenar; el seguidor de
rutas frena ante lo que ve).
"""
from control.avoidance.base import AvoidancePlugin

PLUGIN = AvoidancePlugin(
    name="learned",
    label="Aprendida por el propio algoritmo",
    short_label="Aprendida",
    description="Sin capa adicional: el algoritmo de navegación aprende a esquivar con el LiDAR.",
    build=lambda config: None,
)
