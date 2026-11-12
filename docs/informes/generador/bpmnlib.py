"""Pequeña librería para dibujar diagramas BPMN 2.0 con matplotlib.
Unidades: 1 unidad = 0,1 pulgada. Eje y crece hacia arriba."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, FancyArrowPatch
import numpy as np
matplotlib.rcParams["font.family"]="Carlito"

INK = "#1b1f24"
LANE_FILL = ["#f6f8fb", "#ffffff"]
TASK_FILL = "#ffffff"
FS = 7.4


class BPMN:
    def __init__(self, w, h, title=None):
        self.w, self.h = w, h
        self.fig = plt.figure(figsize=(w / 10, h / 10))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(0, h)
        self.ax.axis("off")
        self.ax.set_aspect("equal")
        if title:
            self.ax.text(w / 2, h - 1.6, title, ha="center", va="center", fontsize=9, fontweight="bold", color=INK)

    # ---------- contenedores ----------
    def pool(self, x, y, w, h, label, blackbox=False):
        self.ax.add_patch(Rectangle((x, y), w, h, fill=False, ec=INK, lw=1.1, zorder=1))
        if not blackbox:
            self.ax.add_patch(Rectangle((x, y), 3, h, fill=True, fc="#e9edf3", ec=INK, lw=1.1, zorder=1))
            self.ax.text(x + 1.5, y + h / 2, label, rotation=90, ha="center", va="center", fontsize=FS + 0.4,
                         fontweight="bold", color=INK, zorder=2)
        else:
            self.ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=FS + 0.6,
                         fontweight="bold", color=INK, zorder=2)

    def lane(self, x, y, w, h, label, i=0):
        self.ax.add_patch(Rectangle((x, y), w, h, fc=LANE_FILL[i % 2], ec=INK, lw=0.8, zorder=0.5))
        self.ax.add_patch(Rectangle((x, y), 3, h, fill=False, ec=INK, lw=0.8, zorder=1))
        self.ax.text(x + 1.5, y + h / 2, label, rotation=90, ha="center", va="center", fontsize=FS,
                     color=INK, zorder=2)

    # ---------- nodos ----------
    def task(self, cx, cy, label, kind=None, w=13, h=7, sub=False):
        x, y = cx - w / 2, cy - h / 2
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.1",
                                         fc=TASK_FILL, ec=INK, lw=1.0, zorder=3))
        self.ax.text(cx, cy + (0.3 if sub else 0), label, ha="center", va="center", fontsize=FS, color=INK,
                     zorder=4, linespacing=1.05)
        if kind:
            self._task_marker(x + 1.3, y + h - 1.3, kind)
        if sub:
            self.ax.add_patch(Rectangle((cx - 0.8, y + 0.15), 1.6, 1.6, fill=False, ec=INK, lw=0.8, zorder=4))
            self.ax.plot([cx - 0.5, cx + 0.5], [y + 0.95, y + 0.95], color=INK, lw=0.8, zorder=5)
            self.ax.plot([cx, cx], [y + 0.45, y + 1.45], color=INK, lw=0.8, zorder=5)
        return dict(x=x, y=y, w=w, h=h, cx=cx, cy=cy)

    def _task_marker(self, mx, my, kind):
        ax = self.ax
        if kind == "user":
            ax.add_patch(Circle((mx, my + 0.25), 0.33, fc="white", ec=INK, lw=0.6, zorder=5))
            ax.add_patch(FancyBboxPatch((mx - 0.6, my - 0.75), 1.2, 0.7, boxstyle="round,pad=0,rounding_size=0.3",
                                        fc="white", ec=INK, lw=0.6, zorder=5))
        elif kind == "service":
            ax.add_patch(Circle((mx, my), 0.55, fc="white", ec=INK, lw=0.6, zorder=5))
            for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                ax.plot([mx + 0.55 * np.cos(a), mx + 0.85 * np.cos(a)], [my + 0.55 * np.sin(a), my + 0.85 * np.sin(a)],
                        color=INK, lw=0.7, zorder=5)
            ax.add_patch(Circle((mx, my), 0.2, fc="white", ec=INK, lw=0.5, zorder=6))
        elif kind in ("send", "receive"):
            self._envelope(mx, my, 1.4, 0.95, filled=(kind == "send"))
        elif kind == "manual":
            ax.add_patch(Rectangle((mx - 0.6, my - 0.5), 1.2, 1.0, fill=False, ec=INK, lw=0.6, zorder=5))
            ax.plot([mx - 0.6, mx + 0.6], [my, my], color=INK, lw=0.5, zorder=5)

    def _envelope(self, cx, cy, w, h, filled=False):
        fc = INK if filled else "white"
        lc = "white" if filled else INK
        self.ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc=fc, ec=INK, lw=0.6, zorder=6))
        self.ax.plot([cx - w / 2, cx, cx + w / 2], [cy + h / 2, cy, cy + h / 2], color=lc, lw=0.6, zorder=7)

    def event(self, cx, cy, kind="start", marker=None, label=None, r=1.6, label_pos="below"):
        ax = self.ax
        if kind == "start":
            ax.add_patch(Circle((cx, cy), r, fc="white", ec=INK, lw=1.0, zorder=3))
        elif kind == "end":
            ax.add_patch(Circle((cx, cy), r, fc="white", ec=INK, lw=2.6, zorder=3))
        else:  # intermedio
            ax.add_patch(Circle((cx, cy), r, fc="white", ec=INK, lw=0.9, zorder=3))
            ax.add_patch(Circle((cx, cy), r - 0.35, fc="white", ec=INK, lw=0.9, zorder=3))
        if marker == "message":
            self._envelope(cx, cy, r * 1.0, r * 0.7, filled=(kind in ("end", "throw")))
        elif marker == "timer":
            ax.add_patch(Circle((cx, cy), r * 0.62, fc="white", ec=INK, lw=0.6, zorder=6))
            ax.plot([cx, cx], [cy, cy + r * 0.48], color=INK, lw=0.6, zorder=7)
            ax.plot([cx, cx + r * 0.35], [cy, cy], color=INK, lw=0.6, zorder=7)
        elif marker == "conditional":
            w_, h_ = r * 0.9, r * 1.1
            ax.add_patch(Rectangle((cx - w_ / 2, cy - h_ / 2), w_, h_, fc="white", ec=INK, lw=0.6, zorder=6))
            for k in range(4):
                yy = cy - h_ / 2 + h_ * (k + 1) / 5
                ax.plot([cx - w_ / 2 + 0.15, cx + w_ / 2 - 0.15], [yy, yy], color=INK, lw=0.5, zorder=7)
        elif marker == "terminate":
            ax.add_patch(Circle((cx, cy), r * 0.6, fc=INK, ec=INK, zorder=6))
        if label:
            if label_pos == "below":
                ax.text(cx, cy - r - 0.5, label, ha="center", va="top", fontsize=FS - 0.6, color=INK, zorder=4,
                        linespacing=1.0)
            elif label_pos == "above":
                ax.text(cx, cy + r + 0.5, label, ha="center", va="bottom", fontsize=FS - 0.6, color=INK, zorder=4,
                        linespacing=1.0)
            elif label_pos == "right":
                ax.text(cx + r + 0.5, cy, label, ha="left", va="center", fontsize=FS - 0.6, color=INK, zorder=4,
                        linespacing=1.0)
            elif label_pos == "left":
                ax.text(cx - r - 0.5, cy, label, ha="right", va="center", fontsize=FS - 0.6, color=INK, zorder=4,
                        linespacing=1.0)
        return dict(cx=cx, cy=cy, r=r)

    def boundary_timer(self, task, label=None, frac=0.75):
        cx = task["x"] + task["w"] * frac
        cy = task["y"]
        e = self.event(cx, cy, "inter", "timer", r=1.3)
        if label:
            self.ax.text(cx + 1.6, cy - 1.2, label, fontsize=FS - 0.8, ha="left", va="top", color=INK, zorder=4)
        return e

    def gateway(self, cx, cy, kind="x", label=None, s=2.3, label_pos="above"):
        pts = [(cx, cy + s), (cx + s, cy), (cx, cy - s), (cx - s, cy)]
        self.ax.add_patch(Polygon(pts, closed=True, fc="white", ec=INK, lw=1.0, zorder=3))
        d = s * 0.38
        if kind == "x":
            self.ax.plot([cx - d, cx + d], [cy - d, cy + d], color=INK, lw=1.3, zorder=4)
            self.ax.plot([cx - d, cx + d], [cy + d, cy - d], color=INK, lw=1.3, zorder=4)
        elif kind == "+":
            self.ax.plot([cx - d * 1.2, cx + d * 1.2], [cy, cy], color=INK, lw=1.3, zorder=4)
            self.ax.plot([cx, cx], [cy - d * 1.2, cy + d * 1.2], color=INK, lw=1.3, zorder=4)
        elif kind == "event":
            self.ax.add_patch(Circle((cx, cy), s * 0.48, fill=False, ec=INK, lw=0.7, zorder=4))
            self.ax.add_patch(Circle((cx, cy), s * 0.38, fill=False, ec=INK, lw=0.7, zorder=4))
            r = s * 0.25
            pent = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, 6)[:-1]]
            self.ax.add_patch(Polygon(pent, closed=True, fill=False, ec=INK, lw=0.6, zorder=5))
        if label:
            if label_pos == "above":
                self.ax.text(cx, cy + s + 0.5, label, ha="center", va="bottom", fontsize=FS - 0.6, color=INK, zorder=4)
            elif label_pos == "below":
                self.ax.text(cx, cy - s - 0.5, label, ha="center", va="top", fontsize=FS - 0.6, color=INK, zorder=4)
        return dict(cx=cx, cy=cy, s=s)

    # ---------- flujos ----------
    def flow(self, pts, label=None, lpos=None, lalign="left"):
        xs, ys = zip(*pts)
        self.ax.plot(xs[:-1] + (xs[-1],), ys, color=INK, lw=0.9, zorder=2, solid_capstyle="butt")
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        self._head(x1, y1, x2, y2, filled=True)
        if label:
            lx, ly = lpos if lpos else ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2 + 0.5)
            self.ax.text(lx, ly, label, fontsize=FS - 0.8, ha=lalign, va="bottom", color=INK, zorder=4,
                         bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9))

    def msg(self, pts, label=None, lpos=None, lalign="left"):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=INK, lw=0.8, ls=(0, (4, 2.5)), zorder=2)
        self.ax.add_patch(Circle(pts[0], 0.45, fc="white", ec=INK, lw=0.7, zorder=3))
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        self._head(x1, y1, x2, y2, filled=False)
        if label:
            lx, ly = lpos if lpos else ((pts[0][0] + pts[1][0]) / 2 + 0.6, (pts[0][1] + pts[1][1]) / 2)
            self.ax.text(lx, ly, label, fontsize=FS - 1.0, ha=lalign, va="center", color="#33415c", style="italic",
                         zorder=4, bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.9))

    def _head(self, x1, y1, x2, y2, filled=True, L=1.1, W=0.5):
        dx, dy = x2 - x1, y2 - y1
        n = (dx ** 2 + dy ** 2) ** 0.5 or 1
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        base = (x2 - ux * L, y2 - uy * L)
        pts = [(x2, y2), (base[0] + px * W, base[1] + py * W), (base[0] - px * W, base[1] - py * W)]
        self.ax.add_patch(Polygon(pts, closed=True, fc=INK if filled else "white", ec=INK, lw=0.7, zorder=4))

    def note(self, x, y, text, w=None):
        self.ax.text(x, y, text, fontsize=FS - 0.8, ha="left", va="top", color="#33415c", zorder=4,
                     linespacing=1.15)

    def save(self, path):
        self.fig.savefig(path, dpi=220, facecolor="white")
        plt.close(self.fig)


# helpers de anclaje
def R(n):
    return (n["x"] + n["w"], n["cy"]) if "w" in n else ((n["cx"] + n.get("s", n.get("r", 0))), n["cy"])


def L(n):
    return (n["x"], n["cy"]) if "w" in n else ((n["cx"] - n.get("s", n.get("r", 0))), n["cy"])


def T(n):
    return (n["cx"], n["y"] + n["h"]) if "w" in n else (n["cx"], n["cy"] + n.get("s", n.get("r", 0)))


def B(n):
    return (n["cx"], n["y"]) if "w" in n else (n["cx"], n["cy"] - n.get("s", n.get("r", 0)))
