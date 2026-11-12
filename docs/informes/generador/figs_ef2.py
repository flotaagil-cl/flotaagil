import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from PIL import Image

INK = "#1b1f24"; MUTED = "#5b6573"
DONE = "#2e7d4f"; WIP = "#c98a1b"; FAIL = "#b23b3b"; PLAN = "#8a97a8"

# ---------------- Gantt planificado vs real (corte semana 12)
rows = [  # nombre, plan (a,b), real (a,b) o None, estado real, nota
    ("Fase 1 · Análisis y formulación", (1, 5), (1, 5), "done", "Terminada"),
    ("Fase 2 · Diseño (E-04, E-05)", (6, 7), (6, 12), "done", "Diseño en Informe 2"),
    ("Sprint 0 · Ecosistema GitHub y CI", (6, 7), (12, 12), "done", "Terminado s12"),
    ("H-3 · PoC GPS en segundo plano", (7, 7), (12, 12), "wip", "En curso s12"),
    ("Sprint 1 · Base", (8, 9), None, None, "No iniciado"),
    ("Sprint 2 · Tiempo real y conductor", (10, 11), None, None, "No iniciado"),
    ("Sprint 3 · Despacho y aeropuerto", (12, 13), None, None, "No iniciado"),
    ("Sprint 4 · Control y cierre", (14, 15), None, None, "No iniciado"),
    ("Fase 5 · UAT y paso a producción", (16, 16), None, None, "En riesgo"),
]
W = 16
fig, ax = plt.subplots(figsize=(10.5, 4.6))
n = len(rows)
for i, (name, plan, real, st, note) in enumerate(rows):
    y = n - i
    a, b = plan
    ax.add_patch(Rectangle((a - 1, y + 0.02), b - a + 1, 0.30, fc="#e9edf2", ec=PLAN, lw=0.8))
    if real:
        a2, b2 = real
        col = DONE if st == "done" else WIP
        ax.add_patch(Rectangle((a2 - 1, y - 0.34), b2 - a2 + 1, 0.30, fc=col, ec="white", lw=1.0,
                               hatch="////" if st == "wip" else None))
        xe = max(b, b2)
    else:
        xe = b
    ax.text(16.25, y - 0.05, note, va="center", fontsize=7.8, color=INK)
ax.axvspan(12, 16, color="#fbf3e4", zorder=0)
ax.text(14, -0.55, "Semanas 13–16:\nre-planificación a validar en la EF2", ha="center", fontsize=7.8, color=MUTED)
ax.axvline(12, color=FAIL, lw=1.0, ls=(0, (3, 2)))
ax.text(11.9, n + 0.55, "Corte EF2 · 28/10 (s12)", ha="right", fontsize=7.6, color=FAIL)
ax.set_yticks([n - i for i in range(n)])
ax.set_yticklabels([r[0] for r in rows], fontsize=8.3)
ax.set_xticks([i + 0.5 for i in range(W)])
ax.set_xticklabels([f"S{i + 1}" for i in range(W)], fontsize=7.8)
ax.set_xlim(0, W + 2.6)
ax.set_ylim(-0.9, n + 0.9)
for x in range(W + 1):
    ax.axvline(x, color="#eef1f4", lw=0.6, zorder=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_xlabel("Semana del proyecto", fontsize=8.4, color=MUTED)
ax.legend(handles=[Patch(fc="#e9edf2", ec=PLAN, label="Plan (Informe 1)"), Patch(fc=DONE, label="Real: terminado"),
                   Patch(fc=WIP, hatch="////", ec="white", label="Real: en curso")],
          loc="upper center", bbox_to_anchor=(0.42, -0.16), ncol=3, fontsize=7.8, frameon=False)
plt.tight_layout()
fig.savefig("fig/gantt_ef2.png", dpi=220, facecolor="white")
plt.close(fig)

# ---------------- PoC H-3: intervalo máximo con pantalla apagada
tests = [("D1\nsin ajustes*", 225.0, False), ("D2\nprioridad del WebView*", 348.9, False),
         ("D3\nvisibilidad + HyperOS\nconfigurado", 34.8, True), ("D3b\nsolo HyperOS\nconfigurado", 260.7, False),
         ("E2 parcial\nversión final, sin cable\n(26,6 min)", 34.9, True)]
fig, ax = plt.subplots(figsize=(8.6, 3.6))
xs = range(len(tests))
for x, (lab, v, ok) in zip(xs, tests):
    ax.bar(x, v, width=0.5, color=DONE if ok else FAIL, zorder=3)
    ax.text(x, v + 6, ("≈ 225 s" if v == 225.0 else f"{v:.1f} s".replace(".", ",")) + (" · pasa" if ok else " · no pasa"),
            ha="center", va="bottom", fontsize=8.2, color=INK)
ax.axhline(60, color=INK, lw=1.0, ls=(0, (4, 3)), zorder=4)
ax.text(-0.45, 64, "Umbral de 60 s (HU-02)", ha="left", va="bottom", fontsize=7.8, color=INK)
ax.set_xticks(list(xs))
ax.set_xticklabels([t[0] for t in tests], fontsize=7.8)
ax.set_ylabel("Intervalo máximo sin posición (s)", fontsize=8.2, color=MUTED)
ax.set_ylim(0, 395)
ax.yaxis.grid(True, color="#eef1f4", lw=0.7, zorder=0)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", labelsize=7.8)
plt.tight_layout()
fig.savefig("fig/h3_intervalos.png", dpi=220, facecolor="white")
plt.close(fig)

# ---------------- capturas del tablero
# Las capturas del tablero (fig/tablero.png y fig/por_sprint.png) ya están recortadas en fig/;
# para rehacerlas, deja las capturas originales en la ruta A y descomenta.
# A = "capturas/"
# im = Image.open(A + "72f19334-image.png").convert("RGB")
# im.crop((0, 115, im.width, im.height - 20)).save("fig/tablero.png")
# im = Image.open(A + "2dc8b173-image.png").convert("RGB")
# im.crop((0, 0, im.width, im.height - 40)).save("fig/por_sprint.png")
print("ok")
