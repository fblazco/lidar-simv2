"""Utilidades geométricas mínimas compartidas por el simulador."""
import math


def wrap_angle(angle: float) -> float:
    """Lleva un ángulo al intervalo (-pi, pi]."""
    wrapped = math.fmod(angle + math.pi, 2.0 * math.pi)
    if wrapped <= 0.0:
        wrapped += 2.0 * math.pi
    return wrapped - math.pi
