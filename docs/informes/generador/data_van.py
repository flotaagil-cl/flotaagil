"""Evaluación económica a tres años: flujo de caja, VAN, TIR y PRI (sección 2.1.9 y Anexo J).

Flujos anuales al cierre de cada año; año 0 = puesta en marcha. Pesos chilenos sin IVA.
Las cifras de planes, consumos y costos fijos son las de la sección 2.1.9.
"""

HORIZONTE = 3
TASA = 0.12
TASAS = (0.08, 0.12, 0.15)

LIC = {"I": 200_000, "E": 350_000, "A": 500_000}
PLAN = {"I": 59_000, "E": 129_000, "A": 199_000}
RESERVAS = {"I": 350, "E": 900, "A": 1_512}
NOMBRE = {"I": "Inicial", "E": "Estándar", "A": "Avanzado"}
FIJO, FIJO_ADIC = 31_150, 8_000
INV_VALORIZADA = 14_047_000
INV_DESEMBOLSO = 847_000          # 770.000 + 10 % de imprevistos

# Consumo mensual por cliente. Avanzado usa el volumen del cliente actual, como en 2.1.9.
CONSUMO = {
    "actual": {"I": 350 * 88, "E": 900 * 88, "A": 132_500},   # WhatsApp vía Twilio + vuelos
    "cc19":   {"I": 350 * 20, "E": 900 * 20, "A": 29_500},    # vuelos + Amazon SES; Web Push sin costo
}
ESCENARIOS = {"actual": "Operación actual (con Twilio)", "cc19": "Con CC-19 (proyección v1.1, sin Twilio)"}

# Costo de desarrollo de CC-19, estimado por componente con la tarifa del presupuesto
# ($1.500.000 mensuales ÷ 108 h ≈ $13.900 por hora) más 10 % de imprevistos. Se invierte en el año 1.
TARIFA_HORA = 13_900
CC19_TAREAS = [
    ("Modelo CONVERSACION y MENSAJE_CHAT, permisos por empresa (RN-13) y retención de 12 meses (RN-15)", 12),
    ("Canal WebSocket del chat (tres tipos de conversación, lectura de la central y auditoría)", 24),
    ("Chat en el portal del pasajero", 16),
    ("Bandeja de conversaciones en el panel de la central", 16),
    ("Chat en la app del conductor con respuestas rápidas", 14),
    ("Verificación de la cuenta por correo (enlace de 24 h)", 8),
    ("Avisos por Web Push y por Amazon SES, con la casilla de aceptación", 20),
    ("Retiro de Twilio y ajuste de HU-20, HU-21, HU-24, HU-30, RN-06 y RN-09", 12),
    ("Pruebas automáticas, casos de prueba y evidencias", 28),
]
CC19_HORAS = sum(h for _, h in CC19_TAREAS)
CC19_COSTO = int(round(CC19_HORAS * TARIFA_HORA * 1.10, -3))

# Cartera activa en cada año: 4 → 7 → 10 clientes; tres nuevos por año, uno de cada plan (el primero es el cliente actual).
CARTERA = {1: ["A", "A", "E", "I"], 2: ["A"] * 3 + ["E"] * 2 + ["I"] * 2, 3: ["A"] * 4 + ["E"] * 3 + ["I"] * 3}
# Sensibilidad: clientes nuevos por año rotando los planes (Avanzado, Estándar, Inicial…).
CARTERA_2_POR_ANIO = {1: ["A", "A", "E"], 2: ["A", "A", "E", "I", "A"], 3: ["A", "A", "E", "I", "A", "E", "I"]}
CARTERA_1_POR_ANIO = {1: ["A", "A"], 2: ["A", "A", "E"], 3: ["A", "A", "E", "I"]}

# Cliente actual (Tabla de beneficio de 2.1.9): escenario meta y escenario prudente (margen 20 %, sin caja).
CLIENTE = {
    "meta": {"licencia": 500_000, "beneficio_mensual": 432_500, "desc": "Escenario meta (margen 25 %, con caja recuperada)"},
    "prudente": {"licencia": 500_000, "beneficio_mensual": 57_800, "desc": "Escenario prudente (margen 20 %, sin caja)"},
}


def detalle_flotaagil(esc, inversion=INV_VALORIZADA, cartera=None):
    cartera = cartera or CARTERA
    filas, previa = [], ["A"]
    flujo0 = -inversion + LIC["A"]
    filas.append(dict(anio=0, clientes=1, planes=0, consumo=0, fijos=0, operacion=0, licencias=LIC["A"],
                      inversion=-inversion, flujo=flujo0))
    for y in range(1, HORIZONTE + 1):
        cart = cartera[y]
        nuevos = list(cart)
        for t in previa:
            nuevos.remove(t)
        planes = sum(PLAN[t] for t in cart) * 12
        consumo = sum(CONSUMO[esc][t] for t in cart) * 12
        fijos = (FIJO + FIJO_ADIC * (len(cart) - 1)) * 12
        oper = planes - consumo - fijos
        lic = sum(LIC[t] for t in nuevos)
        inv = -CC19_COSTO if (esc == "cc19" and y == 1) else 0
        filas.append(dict(anio=y, clientes=len(cart), planes=planes, consumo=consumo, fijos=fijos, operacion=oper,
                          licencias=lic, inversion=inv, flujo=oper + lic + inv))
        previa = cart
    acc = accd = 0
    for f in filas:
        acc += f["flujo"]
        f["acumulado"] = acc
        f["descontado"] = f["flujo"] / (1 + TASA) ** f["anio"]
        accd += f["descontado"]
        f["acum_desc"] = accd
    return filas


def flujos_flotaagil(esc, inversion=INV_VALORIZADA, cartera=None):
    return [f["flujo"] for f in detalle_flotaagil(esc, inversion, cartera)]


def resumen_cartera(lista, esc="actual"):
    """Licencias, contribución, fijos y resultado mensual de una cartera estable (tabla del Anexo J)."""
    lic = sum(LIC[t] for t in lista)
    contrib = sum(PLAN[t] - CONSUMO[esc][t] for t in lista)
    fijos = FIJO + FIJO_ADIC * (len(lista) - 1)
    return lic, contrib, fijos, contrib - fijos


def flujos_cliente(clave):
    c = CLIENTE[clave]
    return [-c["licencia"]] + [c["beneficio_mensual"] * 12] * HORIZONTE


def van(f, r=TASA):
    return sum(x / (1 + r) ** t for t, x in enumerate(f))


def tir(f):
    lo, hi = -0.99, 100.0
    if van(f, lo) * van(f, hi) > 0:
        return None
    for _ in range(300):
        m = (lo + hi) / 2
        if van(f, lo) * van(f, m) <= 0:
            hi = m
        else:
            lo = m
    return m


def pri(f, r=0.0):
    """Período de recuperación en años (interpolado dentro del año). None si no se recupera en el horizonte."""
    acc = 0
    for t, x in enumerate(f):
        d = x / (1 + r) ** t
        if t > 0 and acc + d >= 0:
            return t - 1 + (-acc) / d
        acc += d
    return None


# ---------------------------------------------------------------- formato
def pesos(x):
    s = f"{abs(round(x)):,}".replace(",", ".")
    return ("−$" if x < 0 else "$") + s


def millones(x):
    v = f"{abs(x) / 1e6:,.2f}".replace(".", ",")
    return ("−$" if x < 0 else "$") + v + " M"


def pct(x, dec=1):
    if x is None:
        return "—"
    if x > 10:
        return "> 1.000 %"
    return f"{x * 100:.{dec}f} %".replace(".", ",").replace("-", "−")


def periodo(anios):
    if anios is None:
        return f"No se recupera en {HORIZONTE} años"
    if anios < 1:
        return f"{anios * 12:.1f} meses".replace(".", ",")
    meses = round(anios * 12)
    a, m = divmod(meses, 12)
    txt = f"{a} año" + ("s" if a > 1 else "")
    return txt + (f" y {m} meses" if m > 1 else (" y 1 mes" if m == 1 else ""))


TIR_NO_SIGNIFICATIVA = "No significativa (inversión inicial mínima)"


def tir_texto(f):
    """La TIR deja de tener lectura económica cuando la inversión inicial es mínima frente a los flujos (TIR > 1.000 %)."""
    t = tir(f)
    return TIR_NO_SIGNIFICATIVA if t is not None and t > 10 else pct(t)


def van_con_cartera(esc, cartera3):
    orig = CARTERA[3]
    CARTERA[3] = cartera3
    try:
        return van(flujos_flotaagil(esc))
    finally:
        CARTERA[3] = orig


def indicadores():
    """Filas de la tabla resumen: (evaluación, VAN 8 %, VAN 12 %, VAN 15 %, TIR, PRI)."""
    filas = []
    for clave in ("meta", "prudente"):
        f = flujos_cliente(clave)
        filas.append(("Cliente actual · " + CLIENTE[clave]["desc"], *[pesos(van(f, r)) for r in TASAS], tir_texto(f), periodo(pri(f))))
    for esc in ("actual", "cc19"):
        f = flujos_flotaagil(esc)
        filas.append(("FlotaÁgil · " + ESCENARIOS[esc], *[pesos(van(f, r)) for r in TASAS], pct(tir(f)), periodo(pri(f))))
    return filas


if __name__ == "__main__":
    for row in indicadores():
        print(" | ".join(row))
    for esc in ESCENARIOS:
        print(esc, flujos_flotaagil(esc), "PRI descontado:", periodo(pri(flujos_flotaagil(esc), TASA)))
    print("Incremental CC-19 (VAN 12 %):", pesos(van(flujos_flotaagil("cc19")) - van(flujos_flotaagil("actual"))))
    for esc in ESCENARIOS:
        f = flujos_flotaagil(esc, INV_DESEMBOLSO)
        print("Desembolso", esc, pesos(van(f)), pct(tir(f)), periodo(pri(f)))
