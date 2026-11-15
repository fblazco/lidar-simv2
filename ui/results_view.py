"""Resultados de las corridas terminadas: resumen de una o comparación de dos."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pygame

from optimization.results import RunRecord, compare_runs, list_runs, summary_rows
from ui.training_panel import draw_line_chart
from ui.widgets import ACCENT, GOOD, MUTED, TEXT, WARN, Fonts, Panel, draw_text

COLOR_A, COLOR_B = ACCENT, WARN
ROW = 21
LISTED = 12


class ResultsView:
    def __init__(self, fonts: Fonts, runs_dir: Path, plugins: Dict) -> None:
        self.fonts = fonts
        self.runs_dir = Path(runs_dir)
        self.plugins = plugins
        self.records: List[RunRecord] = []
        self.selected: List[str] = []          # hasta dos corridas: [A, B]

    # --- selección ------------------------------------------------------------
    def refresh(self) -> None:
        self.records = list_runs(self.runs_dir)
        known = {r.run_id for r in self.records}
        self.selected = [run_id for run_id in self.selected if run_id in known]

    def record(self, run_id: str) -> Optional[RunRecord]:
        return next((r for r in self.records if r.run_id == run_id), None)

    def show(self, run_id: str) -> None:
        """Selecciona una corrida recién terminada y, si existe, la última de otro algoritmo para comparar."""
        self.refresh()
        current = self.record(run_id)
        self.selected = [run_id] if current is not None else []
        if current is not None:
            other = next((r for r in self.records if r.strategy != current.strategy), None)
            if other is not None:
                self.selected.append(other.run_id)

    def toggle(self, run_id: str) -> None:
        if run_id in self.selected:
            self.selected.remove(run_id)
        elif len(self.selected) < 2:
            self.selected.append(run_id)
        else:
            self.selected[1] = run_id

    def clear(self) -> None:
        self.selected = []

    def comparison(self) -> list:
        """Filas de la comparación entre A y B (vacío si no hay dos corridas elegidas)."""
        if len(self.selected) < 2:
            return []
        return compare_runs(self.record(self.selected[0]), self.record(self.selected[1]))

    def _short(self, record: RunRecord) -> str:
        plugin = self.plugins.get(record.strategy)
        return plugin.short_label if plugin is not None else record.strategy

    # --- dibujo ------------------------------------------------------------------
    def build_panel(self, panel: Panel) -> None:
        panel.text("Corridas terminadas", ACCENT)
        if not self.records:
            panel.text("Ninguna todavía. Entrena con un algoritmo y pulsa Finalizar.", MUTED)
            return
        panel.text("Pulsa una para ver su resumen; dos, para compararlas.", MUTED, 12)
        for record in self.records[:LISTED]:
            metrics = record.metrics()
            mark = "AB"[self.selected.index(record.run_id)] if record.run_id in self.selected else " "
            label = (f"{mark} {self._short(record)} {metrics['iterations']} gen "
                     f"{metrics['best_fitness']:.0f} {record.finished_at[11:16]}")
            panel.buttons([(label, lambda run_id=record.run_id: self.toggle(run_id),
                            record.run_id in self.selected)], height=23)
        if len(self.records) > LISTED:
            panel.text(f"... y {len(self.records) - LISTED} más en logs/runs/", MUTED, 12)
        panel.buttons([("Quitar selección", self.clear), ("Actualizar", self.refresh)])

    def draw(self, surface, canvas: pygame.Rect) -> None:
        chosen = [self.record(run_id) for run_id in self.selected]
        if not chosen:
            text = "Elige una corrida en el panel" if self.records else "Todavía no hay corridas terminadas"
            draw_text(surface, self.fonts, text, canvas.center, 16, MUTED, "center")
            return
        area = canvas.inflate(-32, -28)
        table_width = int(area.width * 0.56)
        charts = pygame.Rect(area.x + table_width + 16, area.y, area.width - table_width - 16, area.height)
        if len(chosen) == 1:
            self._draw_summary(surface, area, chosen[0], table_width)
            history = chosen[0].stats()
            fitness = [("mejor", GOOD, [h.best_fitness for h in history]),
                       ("promedio", ACCENT, [h.mean_fitness for h in history])]
            success = [("entrenamiento", GOOD, [h.success_rate for h in history])]
            validated = [h.validation_success_rate for h in history if h.validation_success_rate is not None]
            if validated:
                success.append(("validación", WARN, validated))
        else:
            self._draw_comparison(surface, area, chosen[0], chosen[1], table_width)
            first, second = chosen[0].stats(), chosen[1].stats()
            fitness = [("A", COLOR_A, [h.best_fitness for h in first]), ("B", COLOR_B, [h.best_fitness for h in second])]
            success = [("A", COLOR_A, [h.success_rate for h in first]), ("B", COLOR_B, [h.success_rate for h in second])]
        half = (charts.height - 12) // 2
        draw_line_chart(surface, self.fonts, pygame.Rect(charts.x, charts.y, charts.width, half), fitness,
                        "Fitness" if len(chosen) == 1 else "Mejor fitness")
        draw_line_chart(surface, self.fonts, pygame.Rect(charts.x, charts.y + half + 12, charts.width, half), success,
                        "Tasa de éxito", percent=True)

    def _context(self, record: RunRecord) -> str:
        maps = f", más {', '.join(record.fixed_maps)}" if record.fixed_maps else ""
        return (f"semilla {record.seed}, población {record.population_size}, "
                f"{len(record.training_seeds)} mapas aleatorios{maps}")

    def _draw_summary(self, surface, area: pygame.Rect, record: RunRecord, width: int) -> None:
        draw_text(surface, self.fonts, "Resumen de la corrida", area.topleft, 17, ACCENT)
        draw_text(surface, self.fonts, f"{record.run_id}  ({record.finished_at.replace('T', ' ')})",
                  (area.x, area.y + 26), 12, MUTED)
        y = area.y + 54
        for label, text in summary_rows(record):
            draw_text(surface, self.fonts, label, (area.x, y), 13, MUTED)
            draw_text(surface, self.fonts, text[:40], (area.x + int(width * 0.52), y), 13, TEXT)
            y += ROW
        draw_text(surface, self.fonts, self._context(record), (area.x, y + 10), 12, MUTED)

    def _draw_comparison(self, surface, area: pygame.Rect, a: RunRecord, b: RunRecord, width: int) -> None:
        draw_text(surface, self.fonts, "Comparación de corridas", area.topleft, 17, ACCENT)
        col_a, col_b = area.x + int(width * 0.50), area.x + int(width * 0.76)
        draw_text(surface, self.fonts, "A", (col_a, area.y + 30), 14, COLOR_A)
        draw_text(surface, self.fonts, "B", (col_b, area.y + 30), 14, COLOR_B)
        y = area.y + 54
        for label, text_a, text_b, winner in compare_runs(a, b):
            if label == "Algoritmo":
                text_a, text_b = self._short(a), self._short(b)
            draw_text(surface, self.fonts, label, (area.x, y), 13, MUTED)
            draw_text(surface, self.fonts, text_a, (col_a, y), 13, GOOD if winner == "a" else TEXT)
            draw_text(surface, self.fonts, text_b, (col_b, y), 13, GOOD if winner == "b" else TEXT)
            y += ROW
        draw_text(surface, self.fonts, "En verde, el mejor valor de cada fila.", (area.x, y + 10), 12, MUTED)
        draw_text(surface, self.fonts, f"A: {self._context(a)}", (area.x, y + 30), 12, COLOR_A)
        draw_text(surface, self.fonts, f"B: {self._context(b)}", (area.x, y + 48), 12, COLOR_B)
        if a.training_seeds != b.training_seeds or a.fixed_maps != b.fixed_maps:
            draw_text(surface, self.fonts, "Atención: las corridas no usaron los mismos mapas.",
                      (area.x, y + 70), 12, WARN)
