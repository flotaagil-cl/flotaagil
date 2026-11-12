import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Arc
INK = "#1b1f24"; FS = 8.2
W, H = 104, 100
fig = plt.figure(figsize=(W / 10, H / 10))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off"); ax.set_aspect("equal")


def comp(x, y, name, w=20, h=8, fc="white", stereo="«component»"):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=fc, ec=INK, lw=1.0, zorder=3))
    # icono de componente
    ix, iy = x + w / 2 - 2.6, y + h / 2 - 2.4
    ax.add_patch(Rectangle((ix, iy), 1.8, 1.6, fc="white", ec=INK, lw=0.6, zorder=4))
    ax.add_patch(Rectangle((ix - 0.45, iy + 0.25), 0.9, 0.35, fc="white", ec=INK, lw=0.5, zorder=5))
    ax.add_patch(Rectangle((ix - 0.45, iy + 1.0), 0.9, 0.35, fc="white", ec=INK, lw=0.5, zorder=5))
    ax.text(x - 1.0, y + h / 2 - 1.6, stereo, ha="center", va="center", fontsize=FS - 1.6, style="italic", zorder=4)
    ax.text(x - 0.4, y - 0.8, name, ha="center", va="center", fontsize=FS - 0.4, zorder=4, linespacing=1.0)
    return dict(x=x, y=y, w=w, h=h, top=y + h / 2, bot=y - h / 2, l=x - w / 2, r=x + w / 2)


def assembly(x_req, y_req, x_prov, y_prov, yb, label, lx=None, la="left"):
    """y_req: borde del requeridor; y_prov: borde del proveedor; yb: altura del ball."""
    up = y_req > y_prov  # requeridor arriba
    ax.plot([x_prov, x_prov, x_prov], [y_prov, yb - (1 if up else -1) * 0, yb], color=INK, lw=0.8, zorder=2)
    ax.plot([x_prov, x_prov], [y_prov, yb], color=INK, lw=0.8, zorder=2)
    ax.add_patch(Circle((x_prov, yb), 0.9, fc="white", ec=INK, lw=0.9, zorder=4))
    ys = yb + (1.6 if up else -1.6)
    ax.plot([x_req, x_req, x_prov], [y_req, ys + (0.0), ys], color=INK, lw=0.8, zorder=2) if x_req != x_prov else \
        ax.plot([x_req, x_req], [y_req, ys], color=INK, lw=0.8, zorder=2)
    ax.add_patch(Arc((x_prov, yb), 3.2, 3.2, theta1=0 if up else 180, theta2=180 if up else 360, color=INK, lw=0.9, zorder=4))
    if label:
        ax.text(lx if lx else x_prov + 1.6, yb, label, fontsize=FS - 1.2, ha=la, va="center", style="italic", color="#33415c",
                zorder=6, bbox=dict(fc="white", ec="none", pad=0.15))


def dep(p1, p2, label=None, lpos=None):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="->", ls=(0, (4, 2.5)), color=INK, lw=0.8), zorder=2)
    if label:
        ax.text(*lpos, label, fontsize=FS - 1.6, ha="center", va="center", style="italic", bbox=dict(fc="white", ec="none", pad=0.1))


# ----- clientes -----
gmap = comp(13, 90, "Google Maps\nPlatform", w=18, fc="#f3f5f8", stereo="«external»")
panel = comp(37, 90, "Panel administrativo\n(React + Vite)", w=21)
portal = comp(62, 90, "Portal de solicitud\ny convenios (React)", w=21)
app = comp(87, 90, "App del conductor\n(React + Capacitor)", w=21)

# ----- subsistema backend -----
ax.add_patch(Rectangle((4, 26), 96, 50, fill=False, ec=INK, lw=1.3, zorder=1))
ax.text(98, 27.5, "Las dependencias con Reservas y despacho, Mensajería WhatsApp y Auditoría se detallan en la tabla de componentes.", fontsize=FS - 1.6, ha="right", va="center", style="italic", color="#33415c")
ax.text(6, 74.2, "«subsystem»  Backend FlotaÁgil (Django 5 + Django REST Framework + Channels + Celery)", fontsize=FS + 0.2,
        fontweight="bold", va="center")

auth = comp(16, 64, "Autenticación\ny RBAC (JWT)")
res = comp(40, 64, "Reservas y\ndespacho")
mot = comp(64, 64, "Motor de\nsugerencia")
gw = comp(88, 64, "Gateway tiempo\nreal (Channels)")
flo = comp(16, 49, "Flota (conductores\ny vehículos)")
conv = comp(40, 49, "Convenios")
fila = comp(64, 49, "Fila virtual\naeropuerto")
msg = comp(88, 49, "Mensajería\nWhatsApp")
aud = comp(16, 34, "Auditoría")
cob = comp(40, 34, "Cobros y\nreportes")
vue = comp(64, 34, "Monitoreo de\nvuelos (Celery)")
adv = comp(88, 34, "Adaptador de\nvuelos")

# dependencias internas
dep((res["r"], 64), (mot["l"], 64), "«use»", (52, 65.3))
dep((mot["x"], mot["bot"]), (fila["x"], fila["top"]), "«use»", (66.6, 56.5))
dep((gw["l"] + 2, gw["bot"]), (fila["r"] - 2, fila["top"]), "«use»", (78.5, 56.5))
dep((conv["l"], 49), (flo["r"], 49), "«use»", (28, 50.3))
dep((conv["l"] + 2, conv["bot"]), (aud["r"] - 2, aud["top"]), "«use»", (28.5, 42.0))
dep((cob["x"], cob["top"]), (conv["x"], conv["bot"]), "«use»", (42.6, 41.5))
dep((vue["r"], 34), (adv["l"], 34), "«use»", (76, 35.3))
dep((auth["r"], 64), (res["l"], 64), "«use»", (28, 65.3))

# interfaces proporcionadas por el backend hacia clientes
assembly(34, panel["bot"], 34, 76, 80.0, "IApiRest (HTTPS/JSON)", lx=35.8, la="left")
ax.plot([34, 34], [81.6, 83.0], color=INK, lw=0.8, zorder=2)
ax.plot([34, 84], [83.0, 83.0], color=INK, lw=0.8, zorder=2)
ax.plot([62, 62], [portal["bot"], 83.0], color=INK, lw=0.8, zorder=2)
ax.plot([84, 84], [app["bot"], 83.0], color=INK, lw=0.8, zorder=2)
assembly(92, app["bot"], 92, 76, 80.0, "IRealtime (WSS)", lx=90.2, la="right")
ax.plot([42, 42, 92], [panel["bot"], 84.4, 84.4], color=INK, lw=0.8, zorder=2)
ax.plot([92, 92], [81.6, app["bot"]], color=INK, lw=0.8, zorder=2)
# panel requiere mapas
ax.plot([panel["l"], gmap["r"] + 1.6], [91, 91], color=INK, lw=0.8)
ax.add_patch(Arc((gmap["r"] + 0.9, 91), 3.2, 3.2, theta1=270, theta2=90, color=INK, lw=0.9, zorder=4))
ax.plot([gmap["r"], gmap["r"] + 0.0], [91, 91], color=INK, lw=0.8)
ax.add_patch(Circle((gmap["r"] + 0.9, 91), 0.9, fc="white", ec=INK, lw=0.9, zorder=4))
ax.text(23.3, 93.6, "IMapas", fontsize=FS - 1.2, style="italic", color="#33415c")

# ----- datos y externos -----
pg = comp(16, 11, "PostgreSQL 16\n+ PostGIS 3.4", fc="#f3f5f8", stereo="«database»")
rd = comp(40, 11, "Redis 7", fc="#f3f5f8", stereo="«database»")
tw = comp(66, 11, "WhatsApp Business\nAPI (Twilio)", w=21, fc="#f3f5f8", stereo="«external»")
fa = comp(91, 11, "API de vuelos\n(AeroDataBox)", w=20, fc="#f3f5f8", stereo="«external»")
assembly(16, 26, 16, pg["top"], 19, "ISQL", lx=17.8)
assembly(40, 26, 40, rd["top"], 19, "ICanales / caché", lx=41.8)
assembly(64, 26, 64, tw["top"], 19, "IMensajes", lx=65.8)
assembly(91, 26, 91, fa["top"], 19, "IEstadoVuelo", lx=92.8)
# webhook: Twilio requiere interfaz del backend
ax.plot([71, 71], [tw["top"], 19.4], color=INK, lw=0.8)
ax.add_patch(Arc((71, 21.2), 3.2, 3.2, theta1=180, theta2=360, color=INK, lw=0.9, zorder=4))
ax.plot([71, 71], [26, 21.2], color=INK, lw=0.8)
ax.add_patch(Circle((71, 21.2), 0.9, fc="white", ec=INK, lw=0.9, zorder=4))
ax.text(72.8, 21.4, "IWebhook", fontsize=FS - 1.2, style="italic", color="#33415c", va="center")

fig.savefig("fig/uml_comp.png", dpi=220, facecolor="white")
