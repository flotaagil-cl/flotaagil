import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Carlito"
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

INK = "#1b1f24"; MUTED = "#33415c"
C_ZONE = {"internet": "#f6f8fb", "aws": "#fff7ec", "vpc": "#eef7ee", "subnet": "#e6f2ff", "ext": "#f4f0fa",
          "client": "#f3f5f8", "ec2": "#ffffff"}


class D:
    def __init__(self, w, h):
        self.fig = plt.figure(figsize=(w / 10, h / 10))
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, w); self.ax.set_ylim(0, h)
        self.ax.axis("off"); self.ax.set_aspect("equal")

    def zone(self, x, y, w, h, title, kind, dashed=False, tpos="tl", fs=8.4):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=C_ZONE[kind],
                                         ec=INK, lw=0.9, ls=(0, (5, 3)) if dashed else "-", zorder=0.5))
        if tpos == "tl":
            self.ax.text(x + 1.2, y + h - 1.2, title, ha="left", va="top", fontsize=fs, fontweight="bold", color=INK, zorder=1)
        else:
            self.ax.text(x + w / 2, y + h - 1.2, title, ha="center", va="top", fontsize=fs, fontweight="bold", color=INK, zorder=1)

    def box(self, cx, cy, w, h, title, sub=None, fc="white", fs=8.0, bold=True):
        self.ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                         fc=fc, ec=INK, lw=0.9, zorder=3))
        if sub:
            self.ax.text(cx, cy + h * 0.18, title, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else None, zorder=4,
                         linespacing=1.0)
            self.ax.text(cx, cy - h * 0.2, sub, ha="center", va="center", fontsize=fs - 1.4, color=MUTED, zorder=4, linespacing=1.05)
        else:
            self.ax.text(cx, cy, title, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else None, zorder=4, linespacing=1.05)
        return dict(x=cx - w / 2, y=cy - h / 2, w=w, h=h, cx=cx, cy=cy)

    def arrow(self, pts, label=None, lpos=None, both=False, dashed=False, fs=7.0, ha="center"):
        xs, ys = zip(*pts)
        self.ax.plot(xs[:-1] + (xs[-1],), ys, color=INK, lw=0.9, ls=(0, (4, 2.5)) if dashed else "-", zorder=2)
        self.ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9,
                                                                             mutation_scale=9, shrinkA=0, shrinkB=0), zorder=2)
        if both:
            self.ax.annotate("", xy=pts[0], xytext=pts[1], arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9,
                                                                               mutation_scale=9, shrinkA=0, shrinkB=0), zorder=2)
        if label:
            lx, ly = lpos if lpos else ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            self.ax.text(lx, ly, label, ha=ha, va="center", fontsize=fs, color=MUTED, zorder=5, linespacing=1.0,
                         bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.95))

    def save(self, p):
        self.fig.savefig(p, dpi=220, facecolor="white"); plt.close(self.fig)


# ===================== TOPOLOGÍA DE COMUNICACIONES =====================
d = D(120, 84)
d.zone(2, 2, 30, 80, "Usuarios (red local / móvil)", "client")
pc = d.box(17, 66, 24, 9, "PC de la central", "Navegador · banda ancha\n(red local del cliente)")
cel = d.box(17, 47, 24, 9, "Smartphones de conductores", "App Android (Capacitor)\n4G/5G · GPS")
pax = d.box(17, 28, 24, 9, "Smartphone del pasajero", "Portal web (navegador) y WhatsApp\n(vía red de Meta) · 4G/5G o Wi-Fi")
sup = d.box(17, 11, 24, 8, "PC del supervisor", "Navegador (link de convenio)")

d.zone(38, 2, 44, 80, "AWS us-east-1 (nube pública)", "aws")
r53 = d.box(60, 74, 22, 6, "Route 53", "DNS app.flotaagil.cl")
d.zone(41, 6, 38, 61, "VPC 10.0.0.0/16 · subred pública 10.0.1.0/24", "vpc", fs=7.6)
d.box(60, 59.5, 34, 5, "Security Group: 443/TCP abierto · 22/TCP solo IP del equipo", None, fs=7.0, bold=False)
d.zone(44, 9, 32, 45, "EC2 t4g.small · Docker", "subnet", fs=7.6)
ng = d.box(60, 45, 26, 6, "Nginx (TLS 1.2/1.3)", ":443 → proxy interno")
gu = d.box(52.5, 35, 12, 6, "Gunicorn", ":8000 HTTP", fs=7.4)
da = d.box(67.5, 35, 12, 6, "Daphne", ":8001 WS", fs=7.4)
ce = d.box(52.5, 25, 12, 6, "Celery", "worker + beat", fs=7.4)
rd = d.box(67.5, 25, 12, 6, "Redis", ":6379 (local)", fs=7.4)
pg = d.box(60, 15, 26, 5.5, "PostgreSQL + PostGIS", ":5432 (local)", fs=7.4)

d.zone(88, 2, 30, 80, "Servicios externos (Internet)", "ext")
tw = d.box(103, 70, 26, 8, "Twilio · WhatsApp API", "REST saliente · webhook entrante\nred WhatsApp hacia el pasajero")
fl = d.box(103, 55, 26, 7, "API de vuelos", "AeroDataBox / AeroAPI · HTTPS")
gm = d.box(103, 41, 26, 7, "Google Maps Platform", "Maps JS API · consumida por el panel")
s3 = d.box(103, 27, 26, 7, "Amazon S3", "Respaldos pg_dump cada 6 h · HTTPS")
mo = d.box(103, 12, 26, 9, "Monitoreo", "UptimeRobot (sondeo a :443)\nSentry (eventos HTTPS)\nCloudWatch (métricas)")

# bus de entrada desde Internet
for y in (66, 47, 28, 11):
    d.ax.plot([29, 35], [y, y], color=INK, lw=0.9, zorder=2)
d.ax.plot([35, 35], [11, 66], color=INK, lw=0.9, zorder=2)
d.arrow([(35, 45), (47, 45)], None)
d.ax.text(35.6, 40.5, "Internet\nHTTPS 443\nWSS 443", fontsize=6.8, color=MUTED, ha="left", va="center",
          bbox=dict(fc="white", ec="none", pad=0.2))
d.ax.text(29.8, 49.0, "ping GPS\ncada 5–10 s", fontsize=6.4, color=MUTED, ha="left", va="bottom")
d.arrow([(17, 70.5), (17, 76), (49, 76)], "DNS 53", (31, 77.2))
# webhook entrante
d.arrow([(90, 72), (80, 72), (80, 46), (73, 46)], "webhook\nHTTPS 443", (80, 64))
# salida a servicios externos
d.ax.plot([76, 84], [30, 30], color=INK, lw=0.9, zorder=2)
d.ax.plot([84, 84], [14, 68], color=INK, lw=0.9, zorder=2)
for y in (68, 55, 27, 14):
    d.arrow([(84, y), (90, y)], None)
d.ax.text(84.6, 35.5, "HTTPS 443\nsaliente", fontsize=6.8, color=MUTED, ha="left", va="center", bbox=dict(fc="white", ec="none", pad=0.2))
# interno
d.arrow([(ng["cx"] - 7.5, 42), (52.5, 38)], None)
d.arrow([(ng["cx"] + 7.5, 42), (67.5, 38)], None)
d.arrow([(58.5, 25), (61.5, 25)], None)
d.arrow([(52.5, 32), (52.5, 28)], None)
d.arrow([(67.5, 32), (67.5, 28)], None)
d.arrow([(52.5, 22), (52.5, 17.75)], None)
d.ax.text(17, 38.8, "30–50 conductores · ~300 mensajes GPS/min en hora punta", fontsize=6.4, color=MUTED, ha="center")
d.save("fig/topologia.png")

# ===================== INFRAESTRUCTURA AWS =====================
d = D(120, 80)
d.zone(2, 2, 116, 76, "AWS · región us-east-1 (Virginia del Norte)", "aws")
d.zone(5, 6, 66, 64, "VPC 10.0.0.0/16", "vpc")
d.zone(8, 9, 60, 54, "Zona de disponibilidad us-east-1a · subred pública 10.0.1.0/24", "subnet", fs=7.8)
igw = d.box(38, 66.5, 20, 4.5, "Internet Gateway", None, fs=7.6)
d.zone(11, 12, 40, 44, "EC2 t4g.small (Graviton ARM · 2 vCPU · 2 GiB)", "client", fs=7.6)
d.ax.text(13, 51, "Ubuntu Server 24.04 LTS · Docker Engine + Compose v2", fontsize=6.9, color=MUTED)
cont = [("nginx", "TLS · estáticos React"), ("api", "Django + Gunicorn"), ("ws", "Django + Daphne"),
        ("worker", "Celery worker"), ("beat", "Celery beat"), ("redis", "Redis 7"), ("db", "PostgreSQL 16 + PostGIS 3.4")]
for i, (n, s) in enumerate(cont):
    cx = 21 + (i % 2) * 20; cy = 45 - (i // 2) * 8
    if i == 6:
        cx = 31
    d.box(cx, cy, 17 if i != 6 else 36, 6, f"contenedor {n}", s, fs=7.4)
eip = d.box(60, 50, 13, 6, "Elastic IP", "IPv4 pública", fs=7.4)
sgb = d.box(60, 40, 13, 8, "Security\nGroup", "443 abierto\n22 restringido", fs=7.4)
ebs = d.box(60, 25, 13, 10, "EBS gp3 30 GB", "volumen raíz\ncifrado (KMS)", fs=7.4)
# servicios regionales
s3 = d.box(94, 48, 36, 9, "Amazon S3 · bucket de respaldos", "pg_dump cada 6 h, cifrado (SSE-S3)\nciclo de vida: 30 días · acceso por rol IAM")
dlm = d.box(94, 62, 36, 9, "Snapshots EBS (Data Lifecycle Manager)", "cada 6 horas · retención 7 días\n(respaldo de máquina completa)")
cw = d.box(94, 34, 36, 9, "CloudWatch + SNS", "agente en EC2: CPU, memoria, disco,\nStatusCheck · alarmas por correo")
iam = d.box(94, 21, 36, 7, "IAM", "rol de instancia (S3 PutObject) · MFA en raíz")
r53 = d.box(94, 9.5, 36, 7, "Route 53", "zona flotaagil.cl · registro A → Elastic IP")
d.arrow([(38, 64.25), (38, 56)], None)
d.arrow([(53.5, 50), (51, 50)], None)
d.arrow([(53.5, 25), (51, 25)], None)
d.arrow([(66.5, 25), (72, 25), (72, 62), (76, 62)], "snapshot\ncada 6 h", (72, 55), dashed=True)
d.arrow([(31, 18), (31, 13.5), (74, 13.5), (74, 48), (76, 48)], "pg_dump\ncada 6 h", (74, 40), dashed=True)
d.ax.text(37, 3.6, "Ambientes: desarrollo local (Docker Compose) · CI en GitHub Actions · staging temporal t4g.micro · producción (este diagrama)",
          fontsize=6.8, color=MUTED, ha="center")
d.save("fig/infraestructura.png")

# ===================== ARQUITECTURA DE LA SOLUCIÓN =====================
d = D(120, 92)
layers = [
    (78, 12, "Capa de presentación", "client"),
    (64, 12, "Capa de borde y seguridad", "vpc"),
    (40, 22, "Capa de aplicación (monolito modular Django)", "subnet"),
    (24, 14, "Capa de integración (adaptadores)", "ext"),
    (8, 14, "Capa de datos", "aws"),
]
for y, h, t, k in layers:
    d.zone(14, y, 84, h, "", k)
    d.ax.text(15.5, y + h / 2, t, rotation=90, ha="center", va="center", fontsize=7.4, fontweight="bold")
d.box(31, 84, 22, 7, "Panel administrativo", "React + Vite + TS (PC)", fs=7.6)
d.box(55, 84, 22, 7, "Portal de solicitud", "React (navegador móvil)", fs=7.6)
d.box(79, 84, 22, 7, "App del conductor", "React + Capacitor (Android)", fs=7.6)
d.box(31, 70, 22, 7, "Route 53 (DNS)", "resolución del dominio", fs=7.6)
d.box(55, 70, 22, 7, "Nginx · TLS · HSTS", "proxy inverso · estáticos", fs=7.6)
d.box(79, 70, 22, 7, "JWT + RBAC", "por empresa (RN-13)", fs=7.6)
d.box(31, 56, 22, 7, "API REST (DRF)", "Gunicorn · WSGI", fs=7.6)
d.box(55, 56, 22, 7, "Tiempo real (Channels)", "Daphne · ASGI · WSS", fs=7.6)
d.box(79, 56, 22, 7, "Tareas (Celery)", "worker + beat", fs=7.6)
d.box(55, 45, 70, 6, "Módulos de dominio: reservas y despacho · motor de sugerencia · fila virtual · flota · convenios · cobros y reportes · auditoría · vuelos · mensajería", None, fs=7.0, bold=False)
d.box(31, 31, 22, 7, "Adaptador WhatsApp", "Twilio (REST + webhook)", fs=7.6)
d.box(55, 31, 22, 7, "Adaptador de vuelos", "AeroDataBox / AeroAPI", fs=7.6)
d.box(79, 31, 22, 7, "Mapas", "Google Maps JS API\n(cargada por el panel)", fs=7.6)
d.box(31, 15, 22, 7, "PostgreSQL + PostGIS", "fuente única de verdad", fs=7.6)
d.box(55, 15, 22, 7, "Redis", "canales · caché · broker", fs=7.6)
d.box(79, 15, 22, 7, "S3 + snapshots EBS", "respaldos", fs=7.6)
# transversal
d.zone(100, 8, 18, 82, "", "client")
d.ax.text(109, 87, "Transversal", ha="center", fontsize=7.8, fontweight="bold")
for i, (t, s) in enumerate([("Registro de eventos", "logs JSON · 90 días"), ("Sentry", "errores de app"), ("UptimeRobot", "disponibilidad"),
                            ("CloudWatch", "infraestructura"), ("GitHub Actions", "CI/CD"), ("Gestión de secretos", ".env fuera del repo")]):
    d.box(109, 78 - i * 12, 16, 8, t, s, fs=7.2)
# hardware
d.ax.text(56, 4.5, "Hardware: EC2 t4g.small (2 vCPU ARM, 2 GiB) + EBS gp3 30 GB · PC de la central (Windows 10) · smartphones Android de los conductores",
          ha="center", fontsize=6.9, color=MUTED)
for x in (31, 55, 79):
    d.arrow([(x, 80.5), (55 + (x - 55) * 0.3, 73.5)], None)
d.arrow([(50, 66.5), (31, 59.5)], None)
d.arrow([(55, 66.5), (55, 59.5)], None)
d.arrow([(31, 52.5), (31, 48)], None)
d.arrow([(55, 52.5), (55, 48)], None, both=True)
d.arrow([(79, 48), (79, 52.5)], None)
d.arrow([(31, 42), (31, 34.5)], None)
d.arrow([(55, 42), (55, 34.5)], None)
d.arrow([(43, 42), (43, 15), (42, 15)], None)
d.arrow([(67, 42), (67, 15), (66, 15)], None)
d.arrow([(31, 11.5), (31, 9.6), (79, 9.6), (79, 11.5)], None, dashed=True)
d.ax.text(55, 10.4, "respaldo", fontsize=6.6, color=MUTED, ha="center")
d.save("fig/arquitectura.png")
