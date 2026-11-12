import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import subprocess

INK = "#1b1f24"
rows = [
    ("Fase 1 · Análisis y formulación", 1, 5, "#9fb3c8", "E-01 a E-03"),
    ("Fase 2 · Diseño y prototipado", 6, 7, "#9fb3c8", "E-04 a E-06"),
    ("  Ecosistema GitHub y CI (Sprint 0)", 6, 7, "#c9d6e3", "repo, tablero, reglas"),
    ("  Prueba de concepto GPS segundo plano", 7, 7, "#c9d6e3", "H-3"),
    ("Sprint 1 · Base: reservas, flota, verificación", 8, 9, "#3d6fb6", "45 SP"),
    ("Sprint 2 · Tiempo real y ciclo del conductor", 10, 11, "#3d6fb6", "45 SP"),
    ("Sprint 3 · Despacho asistido, aeropuerto, convenios", 12, 13, "#3d6fb6", "42 SP"),
    ("Sprint 4 · Reportes, chat, control y cierre", 14, 15, "#3d6fb6", "46 SP"),
    ("Fase 5 · UAT, capacitación y paso a producción", 16, 16, "#2e8b57", "E-11 a E-13"),
    ("Documentación: Informe 2 (EF2 / ES2)", 8, 14, "#d9a441", "EF2 s12 · ES2 s14"),
]
miles = [("H-1", 5), ("H-2/H-3", 7), ("H-4", 11), ("EF2", 12), ("ES2", 14), ("H-5", 15), ("H-6", 16)]
W = 16
fig, ax = plt.subplots(figsize=(10.5, 5.0))
for i, (name, a, b, col, note) in enumerate(rows):
    y = len(rows) - i
    ax.add_patch(Rectangle((a - 1, y - 0.32), b - a + 1, 0.64, fc=col, ec=INK, lw=0.6))
    ax.text(b + 0.1, y, note, va="center", fontsize=7.6, color="#33415c")
ax.set_yticks([len(rows) - i for i in range(len(rows))])
ax.set_yticklabels([r[0] for r in rows], fontsize=8.4)
ax.set_xticks([i + 0.5 for i in range(W)])
ax.set_xticklabels([f"S{i + 1}" for i in range(W)], fontsize=8)
ax.set_xlim(0, W + 2.2)
ax.set_ylim(-0.6, len(rows) + 0.8)
for x in range(W + 1):
    ax.axvline(x, color="#e3e7ec", lw=0.6, zorder=0)
for m, w in miles:
    ax.add_patch(Polygon([(w, 0.0), (w + 0.18, -0.3), (w, -0.6), (w - 0.18, -0.3)], closed=True, fc=INK, zorder=5))
    ax.text(w, -0.1 if m not in ("EF2", "ES2") else 0.25, m, ha="center", va="bottom", fontsize=7.2, rotation=0)
    if m in ("EF2", "ES2"):
        ax.axvline(w, color="#b04a4a", lw=0.8, ls=(0, (3, 2)), zorder=1)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.set_xlabel("Semana del proyecto (16 semanas)", fontsize=8.6)
ax.tick_params(axis="y", length=0)
plt.tight_layout()
fig.savefig("fig/gantt.png", dpi=220, facecolor="white")

# ----------------------- Máquina de estados -----------------------
dot = r'''digraph SM {
graph [rankdir=LR, fontname="Carlito", nodesep=0.35, ranksep=0.45, pad=0.2];
node [shape=box, style="rounded,filled", fillcolor="#ffffff", color="#1b1f24", fontname="Carlito", fontsize=11];
edge [fontname="Carlito", fontsize=9, color="#1b1f24", arrowsize=0.7];
ini [shape=circle, label="", width=0.18, style=filled, fillcolor="#1b1f24"];
PC [label="PENDIENTE_\nCONFIRMACION", fillcolor="#fff7ec"];
SOL [label="SOLICITADO"]; ASI [label="ASIGNADO"]; ACE [label="ACEPTADO"]; ENC [label="EN_CAMINO"];
ZON [label="EN_ZONA", fillcolor="#fff7ec"]; ABO [label="PASAJERO_\nA_BORDO"];
FIN [label="FINALIZADO", fillcolor="#e9f5ec"]; CAN [label="CANCELADO", fillcolor="#fbeaea"];
ini -> PC [label="formulario web"];
ini -> SOL [label="despachador /\nconvenio"];
PC -> SOL [label="confirma por\nWhatsApp"];
PC -> CAN [label="cancela o\nexpira (15 min)"];
SOL -> ASI [label="despachador\nconfirma"];
ASI -> SOL [label="rechazo o\n60 s"];
ASI -> ACE [label="conductor\nacepta"];
ACE -> ENC [label="inicia\ntrayecto"];
ENC -> ZON [label="< 150 m del\norigen"];
ZON -> ABO [label="pasajero\na bordo"];
ABO -> FIN [label="registra pago\n(RN-10)"];
SOL -> CAN [label="pasajero (WhatsApp)\no despachador"];
ACE -> CAN [label="despachador"]; ENC -> CAN [label="despachador"];
ZON -> CAN [label="no presentación\n(15 min)"];
ABO -> CAN [label="anulación forzada\n(HU-05)", style=dashed];
{rank=same; FIN; CAN}
}'''
open("fig/estados.dot", "w").write(dot)
subprocess.run(["dot", "-Tpng", "-Gdpi=200", "fig/estados.dot", "-o", "fig/estados.png"], check=True)
