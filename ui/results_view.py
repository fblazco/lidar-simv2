"""Resultados de las corridas terminadas: resumen de una o comparación de dos."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pygame

from optimization.results import METRICS, RunRecord, compare_runs, list_runs, summary_rows, validation_significance
from ui.training_panel import draw_legend, draw_line_chart
from ui.widgets import Toolkit, Ui

MAPS_SHORT = {"free": "libres", "route": "con ruta", "mixed": "mixtos"}
# Métricas (claves de ``METRICS``) que se comparan con barras y las que van en recuadros, en ese orden.
BAR_KEYS = ["validation_success_rate", "validation_collision_rate", "validation_efficiency", "recent_success_rate",
            "recent_collision_rate", "final_success_rate", "path_efficiency"]
BOX_KEYS = ["validation_interval", "validation_time", "min_clearance", "seconds_per_iteration", "best_fitness",
            "mean_time"]
MAX_BARS, MAX_BOXES = 5, 4


class ResultsView:
    def __init__(self, kit: Toolkit, runs_dir: Path, plugins: Dict, avoiders: Optional[Dict] = None) -> None:
        self.kit = kit
        self.fonts = kit.fonts
        self.runs_dir = Path(runs_dir)
        self.plugins = plugins
        self.avoiders = avoiders or {}
        self.records: List[RunRecord] = []
        self.selected: List[str] = []          # hasta dos corridas: [A, B]
        self.detail = False                    # comparación: todas las métricas en vez del resumen
        self._memo: Dict = {}                  # cifras ya calculadas de las corridas listadas

    # --- selección ------------------------------------------------------------
    def refresh(self) -> None:
        self.records = list_runs(self.runs_dir)
        self._memo = {}
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

    def toggle_detail(self) -> None:
        self.detail = not self.detail

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
            return f"validación {metrics['validation_success_rate'] * 100:.0f} %"
        return f"entrenamiento {metrics['recent_success_rate'] * 100:.0f} %"

    def _name(self, record: RunRecord) -> str:
        return f"{self._navigation(record)} + {self._avoidance(record)}"

    def _context(self, record: RunRecord) -> str:
        maps = f", más {', '.join(record.fixed_maps)}" if record.fixed_maps else ""
        return (f"semilla {record.seed}, población {record.population_size}, "
                f"{len(record.training_seeds)} mapas por individuo{maps}")

    def _cached(self, key, make):
        """Cifras derivadas de una corrida: se calculan una vez, no en cada cuadro."""
        if key not in self._memo:
            self._memo[key] = make()
        return self._memo[key]

    @staticmethod
    def _same_maps(a: RunRecord, b: RunRecord) -> bool:
        if (a.training_seeds, a.fixed_maps, a.map_mode) == (b.training_seeds, b.fixed_maps, b.map_mode):
            return True
        return a.resampled and b.resampled and a.seed == b.seed and a.map_mode == b.map_mode

    # --- dibujo ------------------------------------------------------------------
    def draw(self, ui: Ui, inner: pygame.Rect) -> None:
        theme = ui.theme
        compact = inner.width < 1100
        gap = 16
        listing = pygame.Rect(inner.x, inner.y, 250 if compact else 300, inner.height)
        chart_width = 250 if compact else 330
        charts = pygame.Rect(inner.right - chart_width, inner.y, chart_width, inner.height)
        center = pygame.Rect(listing.right + gap, inner.y, charts.x - listing.right - 2 * gap, inner.height)
        self._draw_list(ui, listing)
        chosen = [record for record in (self.record(run_id) for run_id in self.selected) if record is not None]
        if not chosen:
            empty = pygame.Rect(center.x, center.y, charts.right - center.x, inner.height)
            ui.card(empty, fill=theme.soft)
            text = "Elige una corrida de la lista" if self.records else "Todavía no hay corridas terminadas"
            ui.text(text, empty.center, 16, theme.muted, anchor="center")
            return
        if len(chosen) == 1:
            self._draw_summary(ui, center, chosen[0])
        else:
            self._draw_comparison(ui, center, chosen[0], chosen[1])
        self._draw_charts(ui, charts, chosen)

    def _draw_list(self, ui: Ui, rect: pygame.Rect) -> None:
        theme = ui.theme
        ui.card(rect)
        x, width = rect.x + 16, rect.width - 32
        ui.text("Corridas terminadas", (x, rect.y + 16), 18, face="bold")
        hint = ("Elige una para ver su resumen; dos, para compararlas." if self.records
                else "Ninguna todavía. Entrena con una combinación y pulsa Finalizar.")
        y = ui.paragraph(hint, x, rect.y + 44, width, 12) + 6
        footer = rect.bottom - 16 - 36
        row = 48 if rect.height >= 620 else 42
        shown = max(0, (footer - 4 - y) // (row + 6))
        for record in self.records[:shown]:
            cell = pygame.Rect(x, y, width, row)
            picked = record.run_id in self.selected
            self.kit.shapes.rounded(ui.surface, cell, 12, theme.soft if picked or ui.hover(cell) else theme.control,
                                    theme.text if picked else theme.line, 2 if picked else 1)
            left = cell.x + 10
            navigation, avoidance = self.plugins.get(record.strategy), self.avoiders.get(record.avoidance)
            for plugin, fallback in ((navigation, record.strategy), (avoidance, record.avoidance)):
                ui.icon(plugin.icon if plugin is not None else "", (left + 10, cell.centery), 20, theme.text, fallback)
                left += 24
            room = cell.right - 10 - (28 if picked else 0) - left - 4
            name, brief = self._cached(("fila", record.run_id), lambda r=record: (
                self._name(r), f"{r.metrics()['iterations']} gen. · {self._headline(r)}"))
            ui.text(ui.fit(name, room, 13, "bold"), (left + 4, cell.centery - 9), 13, face="bold", anchor="midleft")
            ui.text(ui.fit(brief, room, 12), (left + 4, cell.centery + 9), 12, theme.muted, anchor="midleft")
            if picked:
                order = self.selected.index(record.run_id)
                ui.badge((cell.right - 21, cell.centery), "AB"[order], filled=order == 0)
            ui.hit(cell, lambda run_id=record.run_id: self.toggle(run_id))
            y += row + 6
        if len(self.records) > shown and y + 14 < footer:
            ui.text(f"… y {len(self.records) - shown} más en logs/runs/", (x, y), 12, theme.muted)
        half = (width - 8) // 2
        ui.button((x, footer, half, 36), "Quitar selección", self.clear, size=12)
        ui.button((x + half + 8, footer, half, 36), "Actualizar", self.refresh, size=12)

    def _value(self, ui: Ui, midright, text: str, wins: bool, size: int = 12, height: int = 0) -> pygame.Rect:
        """Un valor alineado a la derecha; el mejor de su fila va resaltado."""
        theme = ui.theme
        rect = pygame.Rect(0, 0, self.fonts.width(text, size, "mono") + (12 if wins else 0), height or size + 8)
        rect.midright = midright
        if wins:
            self.kit.shapes.rounded(ui.surface, rect, 6, theme.primary)
        ui.text(text, rect.center, size, theme.on_primary if wins else theme.text, "mono", "center")
        return rect

    def _draw_table(self, ui: Ui, rect: pygame.Rect, rows, two: bool) -> None:
        """Filas (etiqueta, valor A, valor B, ganador). Con ``two`` en falso solo hay una columna de valores."""
        theme = ui.theme
        ui.card(rect)
        x, right = rect.x + 16, rect.right - 16
        column = min(150, int((rect.width - 32) * 0.27))
        y = rect.y + 12
        if two:
            ui.text("Métrica", (x, y + 11), 12, theme.muted, anchor="midleft")
            ui.badge((right - column - 11, y + 11), "A")
            ui.badge((right - 11, y + 11), "B", filled=False)
            y += 28
        step = max(15, min(22, (rect.bottom - 12 - y) // max(len(rows), 1)))
        size = 13 if step >= 19 else 12
        label_room = right - x - (2 * column if two else column) - 8
        for label, first, second, winner in rows:
            if y + step > rect.bottom - 6:
                break
            pygame.draw.line(ui.surface, theme.line, (x, y), (right, y))
            middle = y + step // 2 + 1
            ui.text(ui.fit(label, label_room, size), (x, middle), size, theme.muted, anchor="midleft")
            if two:
                self._value(ui, (right - column, middle), ui.fit(first, column - 14, size - 1, "mono"), winner == "a",
                            size - 1, step - 2)
                self._value(ui, (right, middle), ui.fit(second, column - 14, size - 1, "mono"), winner == "b", size - 1,
                            step - 2)
            else:
                ui.text(ui.fit(first, column + 60, size, "mono"), (right, middle), size, face="mono", anchor="midright")
            y += step

    def _draw_summary(self, ui: Ui, rect: pygame.Rect, record: RunRecord) -> None:
        theme = ui.theme
        head = pygame.Rect(rect.x, rect.y, rect.width, 112)
        ui.card(head, fill=theme.soft)
        x, width = head.x + 18, head.width - 36
        ui.text("Resumen de la corrida", (x, head.y + 16), 12, theme.muted)
        ui.text(ui.fit(self._name(record), width, 22, "bold"), (x, head.y + 34), 22, face="bold")
        ui.text(ui.fit(f"{record.run_id} · {record.finished_at.replace('T', ' ')}", width, 12, "mono"),
                (x, head.y + 68), 12, theme.muted, "mono")
        ui.text(ui.fit(self._context(record), width, 12), (x, head.y + 88), 12, theme.muted)
        short = {"Algoritmo": self._navigation(record), "Evasión de obstáculos": self._avoidance(record),
                 "Mapas": self._maps(record)}
        rows = self._cached(("resumen", record.run_id), lambda: [
            (label, short.get(label, text), "", None) for label, text in summary_rows(record)])
        self._draw_table(ui, pygame.Rect(rect.x, head.bottom + 16, rect.width, rect.height - head.height - 16), rows,
                         two=False)

    def _draw_comparison(self, ui: Ui, rect: pygame.Rect, a: RunRecord, b: RunRecord) -> None:
        theme = ui.theme
        pair = (a.run_id, b.run_id)
        verdict = self._cached(("veredicto", pair), lambda: validation_significance(a, b))
        rows = self._cached(("comparación", pair), lambda: compare_runs(a, b))
        x, width = rect.x + 18, rect.width - 36
        size = 22 if rect.width >= 520 else 18
        title = self.fonts.wrap(f"{self._name(a)} frente a {self._name(b)}", width, size, "bold")[:2]
        notes = self.fonts.wrap(verdict, width, 13)[:3] if verdict else []
        warn = not self._same_maps(a, b)
        height = 16 + 20 + len(title) * (size + 6) + (len(notes) * 17 + 6 if notes else 0) + (21 if warn else 0) + 44
        head = pygame.Rect(rect.x, rect.y, rect.width, height)
        ui.card(head, fill=theme.soft)
        y = head.y + 16
        ui.text("Comparación de dos corridas", (x, y), 12, theme.muted)
        y += 20
        for line in title:
            ui.text(line, (x, y), size, face="bold")
            y += size + 6
        for line in notes:
            ui.text(line, (x, y), 13, theme.muted)
            y += 17
        y += 6 if notes else 0
        if warn:
            ui.text(ui.fit("Atención: las corridas no usaron los mismos mapas.", width, 13, "bold"), (x, y), 13,
                    face="bold")
            y += 21
        toggle = pygame.Rect(head.right - 18 - 158, y, 158, 30)
        ui.button(toggle, "Ver el resumen" if self.detail else "Todas las métricas", self.toggle_detail, "control", size=12)
        room = (toggle.x - x - 16) // 2 - 30
        left = x
        for letter, record, filled in (("A", a, True), ("B", b, False)):
            ui.badge((left + 11, y + 15), letter, filled)
            if room > 40:
                ui.text(ui.fit(self._name(record), room, 13), (left + 28, y + 15), 13, anchor="midleft")
            left += 30 + max(room, 0) + 8
        body = pygame.Rect(rect.x, head.bottom + 16, rect.width, rect.bottom - head.bottom - 16)
        if self.detail:
            short = {"Algoritmo": (self._navigation(a), self._navigation(b)),
                     "Evasión de obstáculos": (self._avoidance(a), self._avoidance(b)),
                     "Mapas": (self._maps(a), self._maps(b))}
            self._draw_table(ui, body, [(label, *short.get(label, (first, second)), winner)
                                        for label, first, second, winner in rows], two=True)
            return
        self._draw_bars(ui, body, a, b, rows)

    def _draw_bars(self, ui: Ui, body: pygame.Rect, a: RunRecord, b: RunRecord, rows) -> None:
        """Lo esencial de una comparación: barras para los porcentajes y recuadros para el resto."""
        theme = ui.theme
        first = self._cached(("métricas", a.run_id), a.metrics)
        second = self._cached(("métricas", b.run_id), b.metrics)
        info = {key: (label, kind, better) for key, label, kind, better, _ in METRICS}
        texts = {label: (text_a, text_b, winner) for label, text_a, text_b, winner in rows}
        boxes = [key for key in BOX_KEYS if first.get(key) is not None or second.get(key) is not None][:MAX_BOXES]
        box_rows = (len(boxes) + 1) // 2
        boxes_height = box_rows * 50 + max(box_rows - 1, 0) * 10
        bars_rect = pygame.Rect(body.x, body.y, body.width,
                                body.height - (boxes_height + 16 if boxes and body.height > 300 else 0))
        ui.card(bars_rect)
        x, width = bars_rect.x + 18, bars_rect.width - 36
        bars = [key for key in BAR_KEYS if info[key][1] == "percent" and first.get(key) is not None
                and second.get(key) is not None]
        bars = bars[:max(1, min(MAX_BARS, (bars_rect.height - 24) // 54))]
        if not bars:
            ui.paragraph("Estas corridas no tienen porcentajes en común para comparar con barras. "
                         "Pulsa Todas las métricas para ver la tabla.", x, bars_rect.y + 16, width, 13)
        step = min(76, (bars_rect.height - 24) // max(len(bars), 1))
        for index, key in enumerate(bars):
            label, _, better = info[key]
            text_a, text_b, winner = texts[label]
            y = bars_rect.y + 14 + index * step
            end = ui.text(ui.fit(label, width - 130, 14, "bold"), (x, y), 14, face="bold").right
            if better == "low":
                ui.text("· menos es mejor", (end + 6, y + 1), 12, theme.muted)
            self._bar(ui, x, y + 22, width, "A", first[key], text_a, winner == "a", True)
            self._bar(ui, x, y + 39, width, "B", second[key], text_b, winner == "b", False)
        if bars_rect.height == body.height:
            return
        half = (body.width - 10) // 2
        for index, key in enumerate(boxes):
            label = info[key][0]
            text_a, text_b, winner = texts[label]
            box = pygame.Rect(body.x + (index % 2) * (half + 10), bars_rect.bottom + 16 + (index // 2) * 60, half, 50)
            ui.card(box, 12, fill=theme.soft)
            ui.text(ui.fit(label, half - 24, 12), (box.x + 12, box.y + 8), 12, theme.muted)
            cursor = box.x + 12
            for letter, text, wins in (("A", text_a, winner == "a"), ("B", text_b, winner == "b")):
                cursor = ui.text(letter, (cursor, box.y + 35), 12, theme.muted, "mono", "midleft").right + 6
                rect = pygame.Rect(0, 0, self.fonts.width(text, 12, "mono") + (12 if wins else 0), 20)
                rect.midleft = (cursor, box.y + 35)
                self._value(ui, rect.midright, text, wins)
                cursor = rect.right + 14

    def _bar(self, ui: Ui, x: int, y: int, width: int, letter: str, value: float, text: str, wins: bool,
             filled: bool) -> None:
        """Barra de 0 a 100 %. Sin colores: A es maciza y B solo tiene contorno."""
        theme = ui.theme
        ui.text(letter, (x, y + 6), 12, theme.muted, "mono", "midleft")
        track = pygame.Rect(x + 18, y + 1, width - 18 - 72, 10)
        self.kit.shapes.rounded(ui.surface, track, 5, theme.track)
        length = int(track.width * max(0.0, min(1.0, value)))
        if length > 0:
            bar = pygame.Rect(track.x, track.y, max(length, 10), 10)
            self.kit.shapes.rounded(ui.surface, bar, 5, theme.primary if filled else theme.background,
                                    None if filled else theme.text, 2)
        self._value(ui, (x + width, y + 6), text, wins)

    def _draw_charts(self, ui: Ui, rect: pygame.Rect, chosen: List[RunRecord]) -> None:
        if len(chosen) == 1:
            history = self._cached(("historial", chosen[0].run_id), chosen[0].stats)
            fitness = [("mejor", [h.best_fitness for h in history]), ("promedio", [h.mean_fitness for h in history])]
            success = [("entrenamiento", [h.success_rate for h in history])]
            validated = [h.validation_success_rate for h in history if h.validation_success_rate is not None]
            if validated and chosen[0].generalizes:
                success.append(("validación", validated))
            titles = ("Fitness", "Tasa de éxito")
        else:
            first = self._cached(("historial", chosen[0].run_id), chosen[0].stats)
            second = self._cached(("historial", chosen[1].run_id), chosen[1].stats)
            fitness = [("A", [h.mean_fitness for h in first]), ("B", [h.mean_fitness for h in second])]
            both_validated = all(record.generalizes and any(h.validation_success_rate is not None for h in history)
                                 for record, history in zip(chosen, (first, second)))
            if both_validated:        # mismos mapas no vistos para ambas: la comparación más justa
                def pick(history):
                    return [h.validation_success_rate for h in history if h.validation_success_rate is not None]
                titles = ("Fitness promedio", "Éxito en validación")
            else:
                def pick(history):
                    return [h.success_rate for h in history]
                titles = ("Fitness promedio", "Éxito en entrenamiento")
            success = [("A", pick(first)), ("B", pick(second))]
        height = (rect.height - 16) // 2
        for index, (title, series, percent) in enumerate(((titles[0], fitness, False), (titles[1], success, True))):
            card = pygame.Rect(rect.x, rect.y + index * (height + 16), rect.width, height)
            ui.card(card)
            ui.text(title, (card.x + 16, card.y + 14), 14, face="bold")
            draw_legend(ui, card.right - 16, card.y + 22, [label for label, _ in series])
            draw_line_chart(ui, (card.x + 16, card.y + 44, card.width - 32, card.height - 56), series, percent)
