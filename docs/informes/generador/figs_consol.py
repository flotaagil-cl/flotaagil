import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
NAVY = "#1F3864"; BLUE = "#2E75B6"; GREY = "#7F7F7F"; ORANGE = "#E67E22"

def box(ax, x, y, w, h, text, fc="#EDEDED", ec=GREY, tc="black", fs=10, bold=False):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.02,rounding_size=0.03", fc=fc, ec=ec, lw=1.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", wrap=True)

def arrow(ax, a, b, label=None, color=NAVY, both=False, off=(0, 0)):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<|-|>" if both else "-|>", color=color, lw=1.6, mutation_scale=14))
    if label:
        mx, my = (a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=8.5, color=color,
                bbox=dict(fc="white", ec="none", pad=1.5))

# ---------------- contexto
fig, ax = plt.subplots(figsize=(13, 8.2)); ax.set_xlim(0, 13); ax.set_ylim(0, 8.2); ax.axis("off")
ax.text(6.5, 7.85, "Diagrama de contexto del sistema — FlotaÁgil", ha="center", fontsize=15, color=NAVY, fontweight="bold")
box(ax, 6.5, 4.1, 3.6, 1.7, "SISTEMA FLOTAÁGIL\n\nPlataforma SaaS de gestión\nde flotas de taxi turismo", fc=NAVY, ec=NAVY, tc="white", fs=11.5, bold=True)
hum = [(1.9, 6.6, "Administrador\nFlota, convenios, configuración\ny reportes", "administra", (0, 0.15)),
       (1.9, 4.1, "Despachador\nReservas, despacho, fila virtual\ny chat con el pasajero", "opera", (0, 0.2)),
       (1.9, 1.6, "Conductor\nApp: turno, viajes, estados,\nubicación y cobro", "usa app móvil", (0, 0.15)),
       (11.1, 6.6, "Pasajero particular\nPortal web y WhatsApp:\nsolicita, confirma, califica", "solicita / responde", (-0.35, 0.0)),
       (11.1, 4.1, "Supervisor de convenio\nReserva por link\na nombre de su empresa", "reserva vía link", (0, 0.2))]
for x, y, t, lab, off in hum:
    box(ax, x, y, 3.3, 1.3, t, fs=9.2)
    a = (x + 1.65, y) if x < 6 else (x - 1.65, y)
    b = (4.7, 4.1 + (y - 4.1) * 0.35) if x < 6 else (8.3, 4.1 + (y - 4.1) * 0.35)
    arrow(ax, a, b, lab, off=off, both=True)
box(ax, 11.1, 1.6, 3.3, 1.5, "Servicios externos\nWhatsApp Business API (Twilio)\nFlightAware AeroAPI (vuelos)\nMapas (Google Maps / OpenStreetMap)", fc="#FCE9D2", ec=ORANGE, fs=9)
arrow(ax, (8.3, 3.5), (9.45, 2.1), "consume APIs /\nrecibe webhooks", color=ORANGE, both=True, off=(0.25, 0.25))
ax.text(6.5, 0.25, "Cinco actores humanos y tres servicios externos. Tarifas, facturación tributaria y mantenimiento de la flota quedan fuera de la frontera.",
        ha="center", fontsize=9, color=GREY, style="italic")
fig.savefig("fig/contexto.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# ---------------- EDT
fig, ax = plt.subplots(figsize=(15, 8)); ax.set_xlim(0, 15); ax.set_ylim(0, 8); ax.axis("off")
ax.text(7.5, 7.65, "Estructura de desglose del trabajo (EDT)", ha="center", fontsize=15, color=NAVY, fontweight="bold")
box(ax, 7.5, 6.85, 4.6, 0.6, "1.0  PROYECTO FLOTAÁGIL (MVP)", fc=NAVY, ec=NAVY, tc="white", fs=12, bold=True)
cols = [("1.1 Gestión\ndel proyecto", ["1.1.1 Plan y backlog", "1.1.2 Control de\ncambios (CC/DC)", "1.1.3 Matriz de riesgos", "1.1.4 Seguimiento de sprints"]),
        ("1.2 Análisis y\nrequerimientos", ["1.2.1 Instrumentos de\nlevantamiento", "1.2.2 Modelo AS-IS", "1.2.3 Product Backlog", "1.2.4 Matriz de\ntrazabilidad"]),
        ("1.3 Diseño y\narquitectura", ["1.3.1 BPMN TO-BE", "1.3.2 Modelo de datos", "1.3.3 Casos de uso y\ncomponentes", "1.3.4 Infraestructura\ny comunicaciones"]),
        ("1.4 Construcción\ndel software", ["1.4.1 Backend, API y\ntiempo real", "1.4.2 Panel web", "1.4.3 Portal y\nverificación WhatsApp", "1.4.4 App del conductor", "1.4.5 Integraciones\n(Twilio, vuelos, mapas)"]),
        ("1.5 Pruebas y\ndespliegue", ["1.5.1 Pruebas automáticas\ny CI", "1.5.2 UAT", "1.5.3 Despliegue en AWS", "1.5.4 Capacitación"])]
for i, (h, items) in enumerate(cols):
    x = 1.5 + i * 3.0
    box(ax, x, 5.6, 2.6, 0.85, h, fc=BLUE, ec=NAVY, tc="white", fs=11, bold=True)
    ax.plot([7.5, 7.5], [6.55, 6.25], color=NAVY, lw=1.8); ax.plot([1.5, 13.5], [6.25, 6.25], color=NAVY, lw=1.8)
    ax.plot([x, x], [6.25, 6.03], color=NAVY, lw=1.8)
    ax.plot([x - 1.15, x - 1.15], [5.17, 4.75 - (len(items) - 1) * 0.82], color=GREY, lw=1.5)
    for j, it in enumerate(items):
        y = 4.75 - j * 0.82
        ax.plot([x - 1.15, x - 1.0], [y, y], color=GREY, lw=1.5)
        box(ax, x + 0.08, y, 2.25, 0.62, it, fc="white", ec=GREY, fs=8.6)
fig.savefig("fig/edt.png", dpi=170, bbox_inches="tight"); plt.close(fig)
print("ok")
