"""Resultados de las corridas terminadas: resumen de una o comparación de dos."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import pygame

from optimization.results import RunRecord, compare_runs, list_runs, summary_rows, validation_significance
from ui.training_panel import draw_line_chart
from ui.widgets import ACCENT, GOOD, MUTED, TEXT, WARN, Fonts, Panel, draw_text

COLOR_A, COLOR_B = ACCENT, WARN
ROW = 19
LISTED = 12
MAPS_SHORT = {"free": "libres", "route": "con ruta", "mixed": "mixtos"}


class ResultsView:
    def __init__(self, fonts: Fonts, runs_dir: Path, plugins: Dict, avoiders: Optional[Dict] = None) -> None:
        self.fonts = fonts
        self.runs_dir = Path(runs_dir)
        self.plugins = plugins
        self.avoiders = avoiders or {}
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
        """Selecciona una corrida recién terminada y, si existe, la última de otra combinación para comparar."""
        self.refresh()
        current = self.record(run_id)
        self.selected = [run_id] if current is not None else []
        if current is not None:
            combination = (current.strategy, current.avoidance)
            other = next((r for r in self.records if (r.strategy, r.avoidance) != combination), None)
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

    def summary(self) -> list:
        """Filas del resumen de la corrida A (vacío si no hay ninguna elegida)."""
        return summary_rows(self.record(self.selected[0])) if self.selected else []

    def comparison(self) -> list:
        """Filas de la comparación entre A y B (vacío si no hay dos corridas elegidas)."""
        if len(self.selected) < 2:
            return []
        return compare_runs(self.record(self.selected[0]), self.record(self.selected[1]))

    def significance(self) -> Optional[str]:
        """Frase sobre si la diferencia de éxito en validación entre A y B es significativa."""
        if len(self.selected) < 2:
            return None
        return validation_significance(self.record(self.selected[0]), self.record(self.selected[1]))

    # --- textos breves -----------------------------------------------------------
    def _navigation(self, record: RunRecord) -> str:
        plugin = self.plugins.get(record.strategy)
        return plugin.short_label if plugin is not None else record.strategy

    def _avoidance(self, record: RunRecord) -> str:
        plugin = self.avoiders.get(record.avoidance)
        return plugin.short_label if plugin is not None else record.avoidance

    @staticmethod
    def _maps(record: RunRecord) -> str:
        if not record.map_mode:
            return "sin dato"
        return f"{MAPS_SHORT.get(record.map_mode, record.map_mode)}, {'nuevos' if record.resampled else 'fijos'}"

    def _headline(self, record: RunRecord) -> str:
        """La cifra que mejor resume una corrida: éxito en validación o, si no aplica, en entrenamiento."""
        metrics = record.metrics()
        if metrics["validation_success_rate"] is not None:
            return f"val {metrics['validation_success_rate'] * 100:.0f}%"
        return f"entr {metrics['recent_success_rate'] * 100:.0f}%"

    # --- dibujo ------------------------------------------------------------------
    def build_panel(self, panel: Panel) -> None:
        panel.text("Corridas terminadas", ACCENT)
        if not self.records:
            panel.text("Ninguna todavía. Entrena con una combinación y pulsa Finalizar.", MUTED)
            return
        panel.text("Pulsa una para ver su resumen; dos, para compararlas.", MUTED, 12)
        for record in self.records[:LISTED]:
            mark = "AB"[self.selected.index(record.run_id)] if record.run_id in self.selected else " "
            label = (f"{mark} {self._navigation(record)}+{self._avoidance(record)} "
                     f"{record.metrics()['iterations']}g {self._headline(record)}")
            panel.buttons([(label[:38], lambda run_id=record.run_id: self.toggle(run_id),
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
        area = canvas.inflate(-32, -24)
        table_width = int(area.width * 0.60)
        charts = pygame.Rect(area.x + table_width + 14, area.y, area.width - table_width - 14, area.height)
        if len(chosen) == 1:
            self._draw_summary(surface, area, chosen[0], table_width)
            history = chosen[0].stats()
            fitness = [("mejor", GOOD, [h.best_fitness for h in history]),
                       ("promedio", ACCENT, [h.mean_fitness for h in history])]
            success = [("entrenamiento", GOOD, [h.success_rate for h in history])]
            validated = [h.validation_success_rate for h in history if h.validation_success_rate is not None]
            if validated and chosen[0].generalizes:
                success.append(("validación", WARN, validated))
            titles = ("Fitness", "Tasa de éxito")
        else:
            self._draw_comparison(surface, area, chosen[0], chosen[1], table_width)
            first, second = chosen[0].stats(), chosen[1].stats()
            fitness = [("A", COLOR_A, [h.mean_fitness for h in first]), ("B", COLOR_B, [h.mean_fitness for h in second])]
            both_validated = all(r.generalizes and r.metrics()["validation_success_rate"] is not None for r in chosen)
            if both_validated:        # mismos mapas no vistos para ambas: la comparación más justa
                def pick(history):
                    return [h.validation_success_rate for h in history if h.validation_success_rate is not None]
                titles = ("Fitness promedio", "Éxito en validación")
            else:
                def pick(history):
                    return [h.success_rate for h in history]
                titles = ("Fitness promedio", "Éxito en entrenamiento")
            success = [("A", COLOR_A, pick(first)), ("B", COLOR_B, pick(second))]
        half = (charts.height - 12) // 2
        draw_line_chart(surface, self.fonts, pygame.Rect(charts.x, charts.y, charts.width, half), fitness, titles[0])
        draw_line_chart(surface, self.fonts, pygame.Rect(charts.x, charts.y + half + 12, charts.width, half), success,
                        titles[1], percent=True)

    def _context(self, record: RunRecord) -> str:
        maps = f", más {', '.join(record.fixed_maps)}" if record.fixed_maps else ""
        return (f"semilla {record.seed}, población {record.population_size}, "
                f"{len(record.training_seeds)} mapas por individuo{maps}")

    def _notes(self, surface, x: int, y: int, width: int, lines) -> None:
        columns = max(20, width // self.fonts.char_width(12))
        for text, color in lines:
            for line in textwrap.wrap(text, columns):
                draw_text(surface, self.fonts, line, (x, y), 12, color)
                y += 16

    def _draw_summary(self, surface, area: pygame.Rect, record: RunRecord, width: int) -> None:
        draw_text(surface, self.fonts, "Resumen de la corrida", area.topleft, 17, ACCENT)
        draw_text(surface, self.fonts, f"{record.run_id}  ({record.finished_at.replace('T', ' ')})",
                  (area.x, area.y + 24), 12, MUTED)
        y = area.y + 48
        short = {"Algoritmo": self._navigation(record), "Evasión de obstáculos": self._avoidance(record),
                 "Mapas": self._maps(record)}
        for label, text in summary_rows(record):
            draw_text(surface, self.fonts, label, (area.x, y), 13, MUTED)
            draw_text(surface, self.fonts, short.get(label, text), (area.x + int(width * 0.60), y), 13, TEXT)
            y += ROW
        self._notes(surface, area.x, y + 8, width - 10, [(self._context(record), MUTED)])

    def _draw_comparison(self, surface, area: pygame.Rect, a: RunRecord, b: RunRecord, width: int) -> None:
        draw_text(surface, self.fonts, "Comparación de corridas", area.topleft, 17, ACCENT)
        col_a, col_b = area.x + int(width * 0.57), area.x + int(width * 0.79)
        draw_text(surface, self.fonts, "A", (col_a, area.y + 26), 14, COLOR_A)
        draw_text(surface, self.fonts, "B", (col_b, area.y + 26), 14, COLOR_B)
        short = {"Algoritmo": (self._navigation(a), self._navigation(b)),
                 "Evasión de obstáculos": (self._avoidance(a), self._avoidance(b)),
                 "Mapas": (self._maps(a), self._maps(b))}
        y = area.y + 48
        for label, text_a, text_b, winner in compare_runs(a, b):
            text_a, text_b = short.get(label, (text_a, text_b))
            draw_text(surface, self.fonts, label, (area.x, y), 13, MUTED)
            draw_text(surface, self.fonts, text_a, (col_a, y), 13, GOOD if winner == "a" else TEXT)
            draw_text(surface, self.fonts, text_b, (col_b, y), 13, GOOD if winner == "b" else TEXT)
            y += ROW
        notes = [("En verde, el mejor valor de cada fila.", MUTED)]
        verdict = validation_significance(a, b)
        if verdict:
            notes.append((verdict, TEXT))
        notes += [(f"A: {self._context(a)}", COLOR_A), (f"B: {self._context(b)}", COLOR_B)]
        if (a.training_seeds, a.fixed_maps, a.map_mode) != (b.training_seeds, b.fixed_maps, b.map_mode) and not (
                a.resampled and b.resampled and a.seed == b.seed and a.map_mode == b.map_mode):
            notes.append(("Atención: las corridas no usaron los mismos mapas.", WARN))
        self._notes(surface, area.x, y + 6, width - 10, notes)
