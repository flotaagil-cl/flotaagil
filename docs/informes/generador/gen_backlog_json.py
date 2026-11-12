import json, re
from collections import defaultdict
from data_backlog import HU, RESP
from data_tests import CP
import sec1  # noqa: just to ensure same source

TIT = {
 "HU-01": "Panel de indicadores de reservas y vehículos",
 "HU-02": "Mapa en tiempo real de conductores",
 "HU-03": "Ingresar, editar y cancelar reservas",
 "HU-04": "Sugerencia del conductor más apto (urbano)",
 "HU-05": "Cierre o anulación forzada de viaje",
 "HU-06": "Reportes operativos y exportación CSV",
 "HU-10": "Administrar conductores y vehículos",
 "HU-11": "Administrar convenios con link y contraseña",
 "HU-12": "Auditoría de cambios en convenios",
 "HU-13": "Estado Disponible/No disponible del conductor",
 "HU-14": "Notificación de viaje asignado",
 "HU-15": "Aceptar o rechazar viaje en 60 s",
 "HU-16": "Estados del viaje y registro de pago",
 "HU-17": "Abrir Google Maps o Waze",
 "HU-18": "Mi turno: viajes completados",
 "HU-19": "Formulario web de solicitud sin cuenta",
 "HU-20": "Verificación del pasajero por WhatsApp",
 "HU-21": "Avisos de estado y cancelación por WhatsApp",
 "HU-24": "Calificación del servicio (1 a 5)",
 "HU-25": "Acceso de convenio con link protegido",
 "HU-26": "Registrar número de vuelo",
 "HU-27": "Monitoreo de vuelo y ajuste de recogida",
 "HU-28": "Alertas de demora, cancelación o desvío",
 "HU-29": "Fila virtual del aeropuerto",
 "HU-30": "Chat de WhatsApp desde el panel",
}
RN = {}
for line in open("sec1.py", encoding="utf-8"):
    m = re.match(r'\s*\("(RN-\d+)", "(.*?)", "(.*?)", "', line)
    if m:
        for h in re.findall(r"HU-\d+", m.group(3)):
            RN.setdefault(h, []).append(m.group(1))
CPS = defaultdict(list)
for c in CP:
    for h in re.findall(r"HU-\d+", c[1]):
        if c[0] not in CPS[h]:
            CPS[h].append(c[0])
DEP = {"HU-27": ["HU-26"], "HU-28": ["HU-26"], "HU-29": ["HU-02", "H-3"], "HU-25": ["HU-11"],
       "HU-30": ["HU-20"], "HU-02": ["H-3"], "HU-04": ["H-3"]}
PAREJA = {"HU-02", "HU-29"}
SLUG = {"Gestión y despacho": "gestion-despacho", "Convenios": "convenios", "Operación en ruta": "operacion-ruta",
        "Módulo pasajero": "modulo-pasajero", "Aeropuerto": "aeropuerto"}
out = []
for h in HU:
    hid, ep, hist, crit, prio, sp, spr, est = h
    out.append({
        "id": hid, "titulo": TIT[hid], "epica": ep, "label_epica": "epica:" + SLUG[ep],
        "historia": hist, "criterios": crit, "prioridad": prio, "sp": sp,
        "sprint": "Sprint " + spr[1], "responsable": RESP.get(hid, "Carlos"),
        "en_pareja": hid in PAREJA, "reglas": RN.get(hid, []), "casos_prueba": CPS.get(hid, []),
        "depende_de": DEP.get(hid, []), "estado_cambio": est,
    })
tareas = [{
    "id": "H-3", "titulo": "Prueba de concepto de GPS en segundo plano", "tipo": "tarea", "sprint": "Sprint 1",
    "responsable": "Renato",
    "descripcion": "Hito H-3, riesgo R-01. Primera tarea del Sprint 1: validar Capacitor + background-geolocation en Android 10+ "
                   "con la pantalla apagada y la app en segundo plano. Resultado: informe técnico corto en docs/ con teléfonos probados, "
                   "frecuencia lograda, consumo de batería y datos. Bloquea HU-02, HU-04 y HU-29.",
}]
assert sum(x["sp"] for x in out) == 178 and len(out) == 25
assert sum(x["sp"] for x in out if x["responsable"] == "Renato") == 89
json.dump({"historias": out, "tareas": tareas}, open("out/github/backlog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for s in "1234":
    print(s, sum(x["sp"] for x in out if x["sprint"].endswith(s)))
print({x["id"]: (x["reglas"], x["casos_prueba"]) for x in out})
