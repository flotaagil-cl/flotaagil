import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle, Circle, Polygon
import numpy as np

INK = "#1b1f24"
FS = 8.6
W, H = 92, 112
fig = plt.figure(figsize=(W / 10, H / 10))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off"); ax.set_aspect("equal")

# límite del sistema
ax.add_patch(Rectangle((21, 21), 50, 88, fill=False, ec=INK, lw=1.2))
ax.text(46, 107.2, "Sistema FlotaÁgil", ha="center", va="center", fontsize=FS + 1.5, fontweight="bold")

EW, EH = 21, 6.2
uc = {}
def usecase(code, name, x, y):
    ax.add_patch(Ellipse((x, y), EW, EH, fc="white", ec=INK, lw=1.0, zorder=3))
    ax.text(x, y + 0.2, f"{code}\n{name}", ha="center", va="center", fontsize=FS - 0.6, zorder=4, linespacing=1.0)
    uc[code] = (x, y)

L, Rx = 34, 58
usecase("CU-05", "Administrar conductores\ny vehículos", L, 100)
usecase("CU-06", "Administrar\nconvenios", L, 92)
usecase("CU-07", "Consultar\nauditoría", L, 84)
usecase("CU-08", "Generar reportes\ny cerrar caja", L, 76)
usecase("CU-02", "Monitorear flota\nen tiempo real", L, 68)
usecase("CU-01", "Gestionar\nreservas", L, 52)
usecase("CU-03", "Asignar viaje\ncon sugerencia", L, 60)
usecase("CU-04", "Cerrar o anular\nviaje en curso", L, 44)
usecase("CU-17", "Atender chat\nde WhatsApp", L, 36)
usecase("CU-15", "Monitorear vuelo y\najustar recogida", L, 28)

usecase("CU-09", "Gestionar estado y\nvehículo activo", Rx, 100)
usecase("CU-10", "Aceptar o rechazar\nviaje asignado", Rx, 92)
usecase("CU-11", "Ejecutar viaje y\nregistrar cobro", Rx, 84)
usecase("CU-16", "Gestionar fila virtual\ndel aeropuerto", Rx, 76)
usecase("CU-12", "Solicitar\nviaje", Rx, 62)
usecase("CU-13", "Verificar teléfono\npor WhatsApp", Rx, 52)
usecase("CU-14", "Recibir avisos,\ncancelar y calificar", Rx, 40)


def actor(x, y, name, side="left"):
    ax.add_patch(Circle((x, y + 3.2), 1.1, fill=False, ec=INK, lw=1.0))
    ax.plot([x, x], [y + 2.1, y - 0.6], color=INK, lw=1.0)
    ax.plot([x - 1.8, x + 1.8], [y + 1.3, y + 1.3], color=INK, lw=1.0)
    ax.plot([x, x - 1.5], [y - 0.6, y - 3.0], color=INK, lw=1.0)
    ax.plot([x, x + 1.5], [y - 0.6, y - 3.0], color=INK, lw=1.0)
    ax.text(x, y - 3.6, name, ha="center", va="top", fontsize=FS, linespacing=1.0)
    return (x, y)


def sysbox(x, y, name):
    ax.add_patch(Rectangle((x - 7.5, y - 3.2), 15, 6.4, fc="#f3f5f8", ec=INK, lw=1.0))
    ax.text(x, y + 1.2, "«sistema»", ha="center", va="center", fontsize=FS - 1.4, style="italic")
    ax.text(x, y - 1.0, name, ha="center", va="center", fontsize=FS - 0.6, linespacing=1.0)
    return (x, y)


def assoc(a, code, dx_a=0):
    x1, y1 = a
    x2, y2 = uc[code]
    # recortar en el borde de la elipse
    ang = np.arctan2(y1 - y2, x1 - x2)
    ex = x2 + (EW / 2) * np.cos(ang)
    ey = y2 + (EH / 2) * np.sin(ang)
    ax.plot([x1 + dx_a, ex], [y1, ey], color=INK, lw=0.8, zorder=2)


adm = actor(9, 90, "Administrador")
des = actor(9, 46, "Despachador")
con = actor(83, 92, "Conductor")
sup = actor(83, 68, "Supervisor de\nconvenio")
pas = actor(83, 48, "Pasajero")
gm = sysbox(9, 68, "Google Maps\nPlatform")
fl = sysbox(9, 24, "API de datos\nde vuelo")
wa = sysbox(83, 36.5, "WhatsApp Business\nAPI (Twilio)")

for c in ["CU-05", "CU-06", "CU-07", "CU-08", "CU-02"]:
    assoc((adm[0], adm[1] + 1.3), c, 1.8)
for c in ["CU-02", "CU-01", "CU-03", "CU-04", "CU-17", "CU-15"]:
    assoc((des[0], des[1] + 1.3), c, 1.8)
for c in ["CU-09", "CU-10", "CU-11", "CU-16"]:
    assoc((con[0], con[1] + 1.3), c, -1.8)
assoc((sup[0], sup[1] + 1.3), "CU-12", -1.8)
for c in ["CU-12", "CU-14"]:
    assoc((pas[0], pas[1] + 1.3), c, -1.8)
assoc((gm[0] + 7.5, gm[1]), "CU-02")
assoc((fl[0] + 7.5, fl[1]), "CU-15")
for c in ["CU-13", "CU-14", "CU-17"]:
    assoc((wa[0] - 7.5, wa[1]), c)


def dep(c_from, c_to, label, lpos):
    x1, y1 = uc[c_from]; x2, y2 = uc[c_to]
    ang = np.arctan2(y2 - y1, x2 - x1)
    sx, sy = x1 + (EW / 2) * np.cos(ang) * 0.98, y1 + (EH / 2) * np.sin(ang) * 0.98
    tx, ty = x2 - (EW / 2) * np.cos(ang) * 0.98, y2 - (EH / 2) * np.sin(ang) * 0.98
    ax.annotate("", xy=(tx, ty), xytext=(sx, sy),
                arrowprops=dict(arrowstyle="->", ls=(0, (4, 2.5)), color=INK, lw=0.8), zorder=2)
    ax.text(lpos[0], lpos[1], label, fontsize=FS - 1.2, ha="center", va="center", style="italic",
            bbox=dict(fc="white", ec="none", pad=0.2), zorder=5)


dep("CU-13", "CU-12", "«extend»\n[solicitud sin convenio]", (Rx - 7.5, 57))
dep("CU-16", "CU-03", "«extend»\n[recogida en aeropuerto]", (51.5, 67.0))

ax.text(46, 18.5, "CU-16 extiende CU-03 en el punto «propuesta de candidato»; "
        "CU-13 extiende CU-12 cuando la\nsolicitud no proviene de un convenio. Los actores «sistema» son servicios externos que participan como actores secundarios.", ha="center", va="top", fontsize=FS - 1.4,
        wrap=True, color="#33415c")
fig.savefig("fig/uml_cu.png", dpi=220, facecolor="white", bbox_inches="tight", pad_inches=0.1)
