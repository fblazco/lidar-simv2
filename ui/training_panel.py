"""Estadísticas del entrenamiento y gráficos de líneas."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import pygame

from optimization.training import IterationStats, TrainingSession
from ui.widgets import ACCENT, BACKGROUND, BORDER, GOOD, MUTED, TEXT, Fonts, Panel, draw_text

Series = Tuple[str, tuple, Sequence[float]]   # (leyenda, color, valores por generación)


def draw_line_chart(surface, fonts: Fonts, rect: pygame.Rect, series: Sequence[Series], title: str = "",
                    percent: bool = False) -> None:
    """Una línea por serie, todas con la misma escala. El eje X es la generación."""
    pygame.draw.rect(surface, BACKGROUND, rect)
    pygame.draw.rect(surface, BORDER, rect, 1)
    x = rect.x + 6
    if title:
        x = draw_text(surface, fonts, title, (x, rect.y + 4), 11, TEXT).right + 10
    for label, color, _ in series:
        x = draw_text(surface, fonts, label, (x, rect.y + 4), 11, color).right + 8
    values = [v for _, _, data in series for v in data]
    if not values:
        draw_text(surface, fonts, "sin generaciones aún", rect.center, 12, MUTED, "center")
        return
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    plot = pygame.Rect(rect.x + 8, rect.y + 24, rect.width - 16, rect.height - 46)   # entre la leyenda y el pie
    steps = max(max(len(data) for _, _, data in series) - 1, 1)
    for _, color, data in series:
        points = [(plot.x + plot.width * i / steps, plot.bottom - plot.height * (v - low) / span)
                  for i, v in enumerate(data)]
        if len(points) == 1:
            pygame.draw.circle(surface, color, (int(points[0][0]), int(points[0][1])), 3)
        elif points:
            pygame.draw.lines(surface, color, False, points, 2)
    scale = (lambda v: f"{v * 100:.0f} %") if percent else (lambda v: f"{v:.0f}")
    draw_text(surface, fonts, scale(high), (rect.right - 6, rect.y + 4), 11, MUTED, "topright")
    draw_text(surface, fonts, scale(low), (rect.right - 6, rect.bottom - 16), 11, MUTED, "topright")
    draw_text(surface, fonts, f"gen 1-{steps + 1}", (rect.x + 6, rect.bottom - 16), 11, MUTED)


def draw_fitness_chart(surface, fonts: Fonts, rect: pygame.Rect, history: List[IterationStats]) -> None:
    """Mejor fitness y fitness promedio por generación."""
    draw_line_chart(surface, fonts, rect, [("mejor", GOOD, [h.best_fitness for h in history]),
                                           ("promedio", ACCENT, [h.mean_fitness for h in history])])


def draw_training_stats(panel: Panel, session: TrainingSession, plugin=None, avoider=None) -> None:
    """Estadísticas generales, las propias del algoritmo (con las etiquetas de su plugin) y el gráfico."""
    done, total = session.evaluated
    limit = f" de {session.max_iterations}" if session.max_iterations else ""
    name = plugin.short_label if plugin is not None else session.strategy.name
    avoidance = avoider.short_label if avoider is not None else session.avoidance
    panel.text(f"{name} + evasión {avoidance}", ACCENT)
    panel.text(f"Generación {session.current_iteration}{limit} · evaluados {done}/{total}")
    panel.text(f"Evaluaciones totales: {session.evaluations + done}", MUTED, 12)
    panel.gap(2)
    last: Optional[IterationStats] = session.history[-1] if session.history else None
    if last is None:
        panel.text("Aún no terminó ninguna generación.", MUTED)
    else:
        episodes = max(last.iteration_episodes, 1)
        panel.text(f"Última generación ({last.iteration})", ACCENT)
        panel.text(f"Fitness  mejor {last.best_fitness:6.1f}  prom. {last.mean_fitness:6.1f}", TEXT, 12)
        panel.text(f"Éxito {last.success_rate * 100:5.1f} %   colisiones {last.collisions / episodes * 100:5.1f} %", TEXT, 12)
        panel.text(f"Eficiencia del camino {last.path_efficiency * 100:5.1f} %", TEXT, 12)
        panel.text(f"Distancia {last.mean_distance:5.1f}   tiempo {last.mean_time:5.1f} s", TEXT, 12)
        if last.validation_fitness is not None:
            crashed = last.validation_collisions / max(last.validation_episodes, 1) * 100
            panel.text(f"Validación ({last.validation_episodes} mapas no vistos)", ACCENT, 12)
            panel.text(f"Éxito {last.validation_success_rate * 100:5.1f} %   colisiones {crashed:5.1f} %", TEXT, 12)
            if last.validation_efficiency is not None:
                panel.text(f"Eficiencia {last.validation_efficiency * 100:5.1f} %   "
                           f"tiempo {last.validation_time:4.1f} s", TEXT, 12)
        elif not session.strategy.generalizes:
            panel.text("Validación: no aplica (una ruta por mapa)", MUTED, 12)
        if last.strategy:
            labels = plugin.stat_labels if plugin is not None else {}
            panel.gap(2)
            for key, value in last.strategy.items():
                panel.text(f"{labels.get(key, key)}: {value:.3g}", MUTED, 12)
    panel.gap(4)
    height = max(70, min(170, panel.rect.bottom - panel.y - 56))   # deja sitio al mensaje de estado
    draw_fitness_chart(panel.surface, panel.fonts, panel.reserve(height), session.history)
