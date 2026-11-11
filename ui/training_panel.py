"""Panel de estadísticas del entrenamiento y gráfico de evolución del fitness."""
from __future__ import annotations

from typing import List

import pygame

from optimization.training import IterationStats, TrainingSession
from ui.widgets import ACCENT, BACKGROUND, BORDER, GOOD, MUTED, TEXT, Fonts, Panel, draw_text

STRATEGY_LABELS = {
    "mutation_rate": "Tasa de mutación",
    "mutation_sigma": "Sigma de mutación",
    "crossover_rate": "Tasa de crossover",
    "elitism": "Elitismo",
    "diversity": "Diversidad genética",
}


def draw_fitness_chart(surface, fonts: Fonts, rect: pygame.Rect, history: List[IterationStats]) -> None:
    """Mejor fitness y fitness promedio por generación."""
    pygame.draw.rect(surface, BACKGROUND, rect)
    pygame.draw.rect(surface, BORDER, rect, 1)
    draw_text(surface, fonts, "mejor", (rect.x + 6, rect.y + 4), 11, GOOD)
    draw_text(surface, fonts, "promedio", (rect.x + 52, rect.y + 4), 11, ACCENT)
    if not history:
        draw_text(surface, fonts, "sin generaciones aún", rect.center, 12, MUTED, "center")
        return
    best = [h.best_fitness for h in history]
    mean = [h.mean_fitness for h in history]
    low, high = min(min(best), min(mean)), max(max(best), max(mean))
    span = (high - low) or 1.0
    plot = rect.inflate(-16, -40)
    plot.y += 10

    def points(values):
        steps = max(len(values) - 1, 1)
        return [(plot.x + plot.width * i / steps, plot.bottom - plot.height * (v - low) / span)
                for i, v in enumerate(values)]

    for values, color in ((mean, ACCENT), (best, GOOD)):
        pts = points(values)
        if len(pts) == 1:
            pygame.draw.circle(surface, color, (int(pts[0][0]), int(pts[0][1])), 3)
        else:
            pygame.draw.lines(surface, color, False, pts, 2)
    draw_text(surface, fonts, f"{high:.0f}", (rect.right - 6, rect.y + 4), 11, MUTED, "topright")
    draw_text(surface, fonts, f"{low:.0f}", (rect.right - 6, rect.bottom - 16), 11, MUTED, "topright")
    draw_text(surface, fonts, f"gen 1-{len(history)}", (rect.x + 6, rect.bottom - 16), 11, MUTED)


def draw_training_stats(panel: Panel, session: TrainingSession) -> None:
    """Estadísticas generales y las propias del algoritmo, más el gráfico."""
    done, total = session.evaluated
    panel.text(f"Generación actual: {session.current_iteration}")
    panel.text(f"Individuos evaluados: {done} / {total}")
    panel.text(f"Evaluaciones totales: {session.evaluations + done}")
    for slot, run in enumerate(session.visible):
        if run is not None:
            panel.text(f" vista {slot + 1}: individuo {run.candidate.id}  fitness {run.partial_fitness:7.1f}", MUTED, 12)
    panel.gap(4)
    last = session.history[-1] if session.history else None
    if last is None:
        panel.text("Aún no terminó ninguna generación.", MUTED)
    else:
        panel.text(f"Última generación ({last.iteration})", ACCENT)
        panel.text(f"Mejor fitness:    {last.best_fitness:8.1f}")
        panel.text(f"Fitness promedio: {last.mean_fitness:8.1f}")
        panel.text(f"Tasa de éxito:    {last.success_rate * 100:7.1f} %")
        panel.text(f"Colisiones:       {last.collisions:8d}")
        panel.text(f"Distancia media:  {last.mean_distance:8.1f}")
        panel.text(f"Tiempo medio:     {last.mean_time:8.1f} s")
        if last.validation_fitness is not None:
            panel.text(f"Validación: fitness {last.validation_fitness:.1f}, "
                       f"éxito {last.validation_success_rate * 100:.0f} %", TEXT, 12)
        if last.strategy:
            panel.gap(4)
            panel.text(f"Algoritmo: {session.strategy.name}", ACCENT)
            for key, value in last.strategy.items():
                panel.text(f"{STRATEGY_LABELS.get(key, key)}: {value:.3g}", TEXT, 12)
    panel.gap(4)
    height = max(80, min(170, panel.rect.bottom - panel.y - 56))   # deja sitio al mensaje de estado
    draw_fitness_chart(panel.surface, panel.fonts, panel.reserve(height), session.history)
