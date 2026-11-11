"""Configuración de pytest: raíz del repo importable y Pygame sin ventana real."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
