"""Gráficos de líneas y tarjetas con las cifras de un entrenamiento."""
from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

import pygame

from optimization.training import IterationStats
from ui.widgets import Ui

Series = Tuple[str, Sequence[float]]      # (leyenda, valores por generación)


def _dashed(surface, color, points, on: float = 5.0, off: float = 4.0, width: int = 2) -> None:
    drawing, left = True, on
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        done = 0.0
        while length - done > 1e-9:
            step = min(left, length - done)
            if drawing:
                pygame.draw.line(surface, color,
                                 (x0 + (x1 - x0) * done / length, y0 + (y1 - y0) * done / length),
                                 (x0 + (x1 - x0) * (done + step) / length, y0 + (y1 - y0) * (done + step) / length), width)
            done += step
            left -= step
            if left <= 1e-9:
                drawing = not drawing
                left = on if drawing else off


def draw_legend(ui: Ui, right: int, center_y: int, labels: Sequence[str]) -> None:
    """Leyenda alineada a la derecha: la primera serie es la línea sólida y la segunda, la cortada."""
    theme = ui.theme
    for index in reversed(range(len(labels[:2]))):
        right = ui.text(labels[index], (right, center_y), 12, theme.muted, anchor="midright").x - 6
        if index == 0:
            pygame.draw.line(ui.surface, theme.text, (right - 18, center_y), (right, center_y), 2)
        else:
            _dashed(ui.surface, theme.muted, [(right - 18, center_y), (right, center_y)], 4, 3)
        right -= 30


def draw_line_chart(ui: Ui, rect, series: Sequence[Series], percent: bool = False) -> None:
    """Hasta dos series con la misma escala; el eje X es la generación.

    Sin colores: la primera serie va en línea sólida y la segunda en línea cortada.
    """
    theme, rect = ui.theme, pygame.Rect(rect)
    plot = pygame.Rect(rect.x, rect.y + 2, rect.width, max(10, rect.height - 22))
    for i in range(4):
        y = plot.y + round(i * (plot.height - 1) / 3)
        pygame.draw.line(ui.surface, theme.line, (plot.x, y), (plot.right - 1, y))
    series = [(label, list(data)) for label, data in series[:2]]
    values = [v for _, data in series for v in data]
    if not values:
        ui.text("sin generaciones aún", plot.center, 12, theme.muted, anchor="center")
        return
    low, high = (0.0, 1.0) if percent else (min(values), max(values))
    span = (high - low) or 1.0
    steps = max(max(len(data) for _, data in series) - 1, 1)
    inner = plot.inflate(0, -8)
    for index in reversed(range(len(series))):          # la sólida se dibuja al final, encima
        data = series[index][1]
        points = [(inner.x + (inner.width - 1) * i / steps, inner.bottom - inner.height * (v - low) / span)
                  for i, v in enumerate(data)]
        color = theme.text if index == 0 else theme.muted
        if len(points) == 1:
            pygame.draw.circle(ui.surface, color, points[0], 3)
        elif index == 0:
            pygame.draw.lines(ui.surface, color, False, points, 2)
            pygame.draw.aalines(ui.surface, color, False, points)
        elif points:
            _dashed(ui.surface, color, points)
    scale = (lambda v: f"{v * 100:.0f} %") if percent else (lambda v: f"{v:.0f}")
    foot = rect.bottom - 7
    ui.text("gen 1", (rect.x, foot), 11, theme.muted, "mono", "midleft")
    ui.text(f"de {scale(low)} a {scale(high)}", (rect.centerx, foot), 11, theme.muted, "mono", "center")
    ui.text(f"gen {steps + 1}", (rect.right, foot), 11, theme.muted, "mono", "midright")


def draw_generation_stats(ui: Ui, rect, last: Optional[IterationStats]) -> None:
    """Tarjeta con las cifras de la última generación terminada."""
    theme, rect = ui.theme, pygame.Rect(rect)
    ui.card(rect)
    x, y = rect.x + 16, rect.y + 14
    if last is None:
        ui.text("Última generación", (x, y), 14, face="bold")
        ui.paragraph("Aún no terminó ninguna generación.", x, y + 28, rect.width - 32, 13)
        return
    ui.text(f"Última generación · {last.iteration}", (x, y), 14, face="bold")
    episodes = max(last.iteration_episodes, 1)
    cells = [("Mejor fitness", f"{last.best_fitness:.1f}"), ("Promedio", f"{last.mean_fitness:.1f}"),
             ("Éxito", f"{last.success_rate * 100:.1f} %"), ("Colisiones", f"{last.collisions / episodes * 100:.1f} %"),
             ("Eficiencia", f"{last.path_efficiency * 100:.1f} %" if last.path_efficiency > 0 else "sin dato"),
             ("Tiempo medio", f"{last.mean_time:.1f} s")]
    column = (rect.width - 32) // 3
    room = rect.bottom - 12 - (y + 28)
    step = max(40, min(56, room // 2))
    size = 20 if column >= 118 else 16
    for index, (label, value) in enumerate(cells):
        ui.stat(x + (index % 3) * column, y + 30 + (index // 3) * step, label, value, size)


def draw_validation(ui: Ui, rect, last: Optional[IterationStats], generalizes: bool) -> None:
    """Tarjeta con el resultado del mejor individuo en los mapas que nunca vio."""
    theme, rect = ui.theme, pygame.Rect(rect)
    ui.card(rect, fill=theme.soft)
    x, y, width = rect.x + 16, rect.y + 14, rect.width - 32
    if not generalizes:
        ui.text("Validación", (x, y), 14, face="bold")
        ui.paragraph("No aplica: este algoritmo aprende una ruta para cada mapa de entrenamiento.", x, y + 28, width, 13)
        return
    if last is None or last.validation_success_rate is None:
        ui.text("Validación", (x, y), 14, face="bold")
        ui.paragraph("Se mide al terminar cada generación, en mapas que no intervienen en el aprendizaje.",
                     x, y + 28, width, 13)
        return
    maps = max(last.validation_episodes, 1)
    ui.text(ui.fit(f"Validación · {last.validation_episodes} mapas no vistos", width, 14, "bold"), (x, y), 14, face="bold")
    big = 42 if rect.height >= 200 else 32
    number = ui.text(f"{last.validation_success_rate * 100:.0f} %", (x, y + 26), big, face="bold")
    reached = round(last.validation_success_rate * maps)
    ui.text(f"llega en {reached} de {maps}", (number.right + 10, number.bottom - 9), 13, theme.muted, anchor="bottomleft")
    foot = rect.bottom - 14 - 34
    if foot > number.bottom:
        ui.divider(x, foot - 8, width)
        column = width // 3
        cells = [("Colisiones", f"{last.validation_collisions / maps * 100:.0f} %"),
                 ("Eficiencia", f"{last.validation_efficiency * 100:.1f} %" if last.validation_efficiency else "sin dato"),
                 ("Tiempo", f"{last.validation_time:.1f} s" if last.validation_time else "sin dato")]
        for index, (label, value) in enumerate(cells):
            ui.stat(x + index * column, foot, label, value, 15)
