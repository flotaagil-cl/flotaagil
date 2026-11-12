"""Carta Gantt: línea base frente al avance al corte de la semana 14."""
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Patch

INK = "#1b1f24"; MUTED = "#5b6573"
DONE = "#2e7d4f"; PROY = "#3d6fb6"; PLAN = "#8a97a8"; WIP = "#c98a1b"

rows = [  # nombre, plan (a,b) o None, real (a,b) o None, estado, nota
    ("Fase 1 · Análisis y formulación", (1, 5), (1, 5), "done", "Terminada"),
    ("Fase 2 · Diseño (E-04, E-05)", (6, 7), (6, 7), "done", "Terminada; corregida tras la EF2"),
    ("Sprint 0 · Ecosistema GitHub y CI", (6, 7), (6, 7), "done", "Terminado"),
    ("H-3 · PoC de GPS en segundo plano", (7, 7), (7, 7), "wip", "Hecha · falta teléfono"),
    ("Sprint 1 · Base (45 SP)", (8, 9), (8, 9), "done", "45 de 45 SP"),
    ("Sprint 2 · Tiempo real y conductor (45 SP)", (10, 11), (10, 11), "done", "45 de 45 SP"),
    ("Sprint 3 · Despacho y aeropuerto (42 SP)", (12, 13), (12, 13), "done", "42 de 42 SP"),
    ("Sprint 4 · Control y cierre (46 SP)", (14, 15), (14, 14), "wip", "En curso · 46 SP construidos"),
    ("  Correcciones de la EF2 (HU-31, HU-32, CP-14)", None, (14, 15), "proy", "8 SP · CC-12 y CC-15"),
    ("Documentación: Informe 2 (EF2 y ES2)", (8, 14), (8, 14), "done", "EF2 s12 · ES2 s14"),
    ("Despliegue en AWS, carga, seguridad y recuperación", None, (15, 15), "proy", "CP-28 a CP-31"),
    ("Capacitación y marcha blanca", (16, 16), (15, 16), "proy", "Adelantada a la s15"),
    ("UAT, corte y cierre (E-11 a E-13)", (16, 16), (16, 16), "proy", "CP-35 · H-6"),
]
miles = [("H-1", 5, 0), ("H-2\nH-3", 7, 0), ("H-4", 11, 0), ("EF2", 12, 1), ("ES2", 14, 1), ("H-5", 15, 0), ("H-6", 16, 0)]
W = 16
n = len(rows)
fig, ax = plt.subplots(figsize=(10.8, 5.9))
ax.axvspan(13, 14, color="#fdf1dc", zorder=0)
for i, (name, plan, real, st, note) in enumerate(rows):
    y = n - i
    if plan:
        a, b = plan
        ax.add_patch(Rectangle((a - 1, y + 0.04), b - a + 1, 0.28, fc="#eef1f5", ec=PLAN, lw=0.8))
    if real:
        a2, b2 = real
        col = {"done": DONE, "wip": WIP, "proy": "white"}[st]
        ax.add_patch(Rectangle((a2 - 1, y - 0.34), b2 - a2 + 1, 0.30, fc=col, ec=PROY if st == "proy" else "white",
                               lw=1.2 if st == "proy" else 1.0, hatch="////" if st in ("proy", "wip") else None))
    ax.text(16.25, y - 0.04, note, va="center", fontsize=7.8, color=INK)
ax.set_yticks([n - i for i in range(n)])
ax.set_yticklabels([r[0] for r in rows], fontsize=8.4)
ax.set_xticks([i + 0.5 for i in range(W)])
ax.set_xticklabels([f"S{i + 1}" for i in range(W)], fontsize=8)
ax.set_xlim(0, W + 3.9)
ax.set_ylim(-1.25, n + 1.0)
for x in range(W + 1):
    ax.axvline(x, color="#e3e7ec", lw=0.6, zorder=0)
for m, w, acad in miles:
    ax.add_patch(Polygon([(w, 0.25), (w + 0.18, -0.05), (w, -0.35), (w - 0.18, -0.05)], closed=True, fc="#b04a4a" if acad else INK, zorder=5))
    ax.text(w, -0.45, m, ha="center", va="top", fontsize=7.4, color="#b04a4a" if acad else INK, linespacing=0.95, zorder=6,
            bbox=dict(fc="white", ec="none", pad=0.6))
    if acad:
        ax.axvline(w, color="#b04a4a", lw=0.8, ls=(0, (3, 2)), zorder=1)
ax.text(13.5, n + 0.72, "Corte: semana 14", ha="center", va="center", fontsize=7.4, color="#8a5a00", zorder=6, bbox=dict(fc="#fdf1dc", ec="none", pad=1.0))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.set_xlabel("Semana del proyecto (semana 1 = 10/08/2026)", fontsize=8.6)
ax.tick_params(axis="y", length=0)
ax.legend(handles=[Patch(fc="#eef1f5", ec=PLAN, label="Línea base (formulación)"), Patch(fc=DONE, ec="white", label="Real, terminado"),
                   Patch(fc=WIP, ec="white", hatch="////", label="Real, en curso o con pendiente"), Patch(fc="white", ec=PROY, hatch="////", label="Replanificado (por ejecutar)")],
          loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=4, fontsize=7.6, frameon=False)
plt.tight_layout()
fig.savefig("fig/gantt.png", dpi=220, facecolor="white")
print("ok")
