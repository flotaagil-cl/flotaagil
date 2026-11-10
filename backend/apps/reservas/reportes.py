"""HU-06: reportes operativos y exportación CSV. Solo el administrador de la empresa.

Cada reporte define sus columnas, y con ellas se arman la pantalla y el CSV: se descarga lo que se ve.

- Liquidación y facturación: viajes FINALIZADOS según el día del pago, en hora de Chile.
- Cancelaciones e historial: según el día de recogida.
- Los cierres forzados (HU-05) entran a la liquidación, identificados como tales.

DC-29 detalla estas definiciones.
"""

import csv
import io
from datetime import date, datetime

from django.db.models import Exists, OuterRef
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Auditoria, Entidad
from apps.comun.permisos import con_roles
from apps.convenios.models import Convenio
from apps.cuentas.models import Rol
from apps.flota.models import Conductor

from .models import Canal, EstadoViaje, MetodoPago, OrigenCancelacion, Viaje

CIERRE = "CIERRE_FORZADO"
ANULACION = "ANULACION_FORZADA"
TEXTO_FORZADO = {CIERRE: "Cierre forzado", ANULACION: "Anulación forzada"}


def _col(clave: str, titulo: str, tipo: str = "texto") -> dict:
    return {"clave": clave, "titulo": titulo, "tipo": tipo}


_DESGLOSE = [_col(m.value.lower(), m.label, "pesos") for m in MetodoPago]
_MONTOS = [
    _col("viajes", "Viajes", "entero"),
    *_DESGLOSE,
    _col("total", "Total", "pesos"),
    _col("cierres_forzados", "Cierres forzados", "entero"),
    _col("monto_cierres_forzados", "Monto de cierres forzados", "pesos"),
]
COLUMNAS = {
    "liquidacion": [_col("dia", "Día", "fecha"), _col("conductor", "Conductor"), *_MONTOS],
    "facturacion": [_col("cliente", "Convenio"), _col("rut", "RUT"), *_MONTOS],
    "cancelaciones": [
        _col("origen", "Origen"),
        _col("cantidad", "Cancelaciones", "entero"),
        _col("tasa", "Tasa sobre las reservas", "porcentaje"),
    ],
    "historial": [
        _col("id", "Reserva", "entero"),
        _col("recogida", "Recogida", "fecha_hora"),
        _col("estado", "Estado"),
        _col("pasajero", "Pasajero"),
        _col("origen", "Origen"),
        _col("destino", "Destino"),
        _col("conductor", "Conductor"),
        _col("convenio", "Convenio"),
        _col("metodo", "Método de pago"),
        _col("monto", "Monto", "pesos"),
        _col("forzado", "Cierre o anulación forzada"),
        _col("calificacion", "Calificación", "entero"),
    ],
    # HU-32 (DC-33): conciliación de las reservas de contingencia con la hoja en papel, por folio.
    "contingencia": [
        _col("folio", "Folio"),
        _col("id", "Reserva", "entero"),
        _col("recogida", "Recogida real", "fecha_hora"),
        _col("resultado", "Resultado"),
        _col("conductor", "Conductor"),
        _col("turno", "Turno"),
        _col("metodo", "Método de pago"),
        _col("monto", "Monto", "pesos"),
        _col("ingresado_por", "Ingresado por"),
        _col("ingresado_en", "Ingresado", "fecha_hora"),
    ],
}


class ParametrosSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    conductor = serializers.IntegerField(required=False)
    convenio = serializers.IntegerField(required=False)

    def validate(self, datos):
        hoy = timezone.localdate()
        datos.setdefault("desde", hoy)
        datos.setdefault("hasta", hoy)
        if datos["desde"] > datos["hasta"]:
            raise serializers.ValidationError(
                {"desde": ["La fecha inicial no puede ser posterior a la final."]}
            )
        return datos


class ColumnaSerializer(serializers.Serializer):
    clave = serializers.CharField()
    titulo = serializers.CharField()
    tipo = serializers.ChoiceField(choices=["texto", "entero", "pesos", "fecha", "fecha_hora", "porcentaje"])


class ReporteSerializer(serializers.Serializer):
    columnas = ColumnaSerializer(many=True)
    filas = serializers.ListField(child=serializers.DictField())
    totales = serializers.DictField(help_text="De todo el período, con las mismas claves de las columnas")
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True, help_text="Solo el historial se pagina")
    previous = serializers.CharField(allow_null=True)


class OpcionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class OpcionesSerializer(serializers.Serializer):
    conductores = OpcionSerializer(many=True)
    convenios = OpcionSerializer(many=True)


def _forzado(accion: str) -> Exists:
    return Exists(Auditoria.objects.filter(entidad=Entidad.VIAJE, entidad_id=OuterRef("pk"), accion=accion))


def _filtrar(viajes, filtros):
    if "conductor" in filtros:
        viajes = viajes.filter(conductor_id=filtros["conductor"])
    if "convenio" in filtros:
        viajes = viajes.filter(convenio_id=filtros["convenio"])
    return viajes


def _finalizados(empresa_id: int, filtros: dict):
    viajes = Viaje.objects.filter(
        empresa_id=empresa_id,
        estado=EstadoViaje.FINALIZADO,
        pago__registrado_en__date__gte=filtros["desde"],
        pago__registrado_en__date__lte=filtros["hasta"],
    )
    return _filtrar(viajes, filtros).select_related("pago").annotate(cierre=_forzado(CIERRE))


def _acumulado() -> dict:
    return {
        "viajes": 0,
        **{m.value.lower(): 0 for m in MetodoPago},
        "total": 0,
        "cierres_forzados": 0,
        "monto_cierres_forzados": 0,
    }


def _sumar(acumulado: dict, viaje) -> None:
    pago = viaje.pago
    acumulado["viajes"] += 1
    acumulado[pago.metodo.lower()] += pago.monto
    acumulado["total"] += pago.monto
    if viaje.cierre:
        acumulado["cierres_forzados"] += 1
        acumulado["monto_cierres_forzados"] += pago.monto


def liquidacion(empresa_id: int, filtros: dict) -> tuple[list, dict]:
    viajes = (
        _finalizados(empresa_id, filtros)
        .select_related("conductor__usuario")
        .annotate(dia=TruncDate("pago__registrado_en", tzinfo=timezone.get_current_timezone()))
    )
    filas: dict = {}
    totales = _acumulado()
    for viaje in viajes:
        nombre = viaje.conductor.usuario.nombre if viaje.conductor else "Sin conductor"
        clave = (viaje.dia, nombre, viaje.conductor_id)
        fila = filas.setdefault(clave, {"dia": viaje.dia, "conductor": nombre, **_acumulado()})
        _sumar(fila, viaje)
        _sumar(totales, viaje)
    orden = sorted(filas, key=lambda c: (c[0], c[1], c[2] or 0))
    return [filas[c] for c in orden], {"conductor": "Total", **totales}


def facturacion(empresa_id: int, filtros: dict) -> tuple[list, dict]:
    viajes = _finalizados(empresa_id, filtros).filter(convenio__isnull=False).select_related("convenio")
    filas: dict = {}
    totales = _acumulado()
    for viaje in viajes:
        convenio = viaje.convenio
        fila = filas.setdefault(
            convenio.pk, {"cliente": convenio.cliente_nombre, "rut": convenio.cliente_rut, **_acumulado()}
        )
        _sumar(fila, viaje)
        _sumar(totales, viaje)
    return sorted(filas.values(), key=lambda f: f["cliente"]), {"cliente": "Total", **totales}


def _por_recogida(empresa_id: int, filtros: dict):
    viajes = Viaje.objects.filter(
        empresa_id=empresa_id,
        recogida_en__date__gte=filtros["desde"],
        recogida_en__date__lte=filtros["hasta"],
    )
    return _filtrar(viajes, filtros)


def _tasa(cantidad: int, total: int) -> float:
    return round(100 * cantidad / total, 1) if total else 0.0


def cancelaciones(empresa_id: int, filtros: dict) -> tuple[list, dict]:
    viajes = _por_recogida(empresa_id, filtros)
    reservas = viajes.count()
    canceladas = list(
        viajes.filter(estado=EstadoViaje.CANCELADO).values_list("origen_cancelacion", flat=True)
    )
    filas = [
        {
            "origen": origen.label,
            "cantidad": canceladas.count(origen.value),
            "tasa": _tasa(canceladas.count(origen.value), reservas),
        }
        for origen in OrigenCancelacion
    ]
    sin_origen = canceladas.count(None)
    if sin_origen:
        filas.append({"origen": "Sin origen", "cantidad": sin_origen, "tasa": _tasa(sin_origen, reservas)})
    return filas, {
        "origen": f"Total, de {reservas} reservas",
        "cantidad": len(canceladas),
        "tasa": _tasa(len(canceladas), reservas),
    }


def _consulta_historial(empresa_id: int, filtros: dict):
    return (
        _por_recogida(empresa_id, filtros)
        .select_related("pasajero", "conductor__usuario", "convenio", "pago", "calificacion")
        .annotate(cierre=_forzado(CIERRE), anulacion=_forzado(ANULACION))
        .order_by("-recogida_en", "-id")
    )


def _fila_historial(viaje) -> dict:
    pago = getattr(viaje, "pago", None)
    calificacion = getattr(viaje, "calificacion", None)
    forzado = TEXTO_FORZADO[CIERRE] if viaje.cierre else TEXTO_FORZADO[ANULACION] if viaje.anulacion else None
    return {
        "id": viaje.pk,
        "recogida": viaje.recogida_en,
        "estado": EstadoViaje(viaje.estado).label,
        "pasajero": viaje.pasajero.nombre,
        "origen": viaje.origen_dir,
        "destino": viaje.destino_dir,
        "conductor": viaje.conductor.usuario.nombre if viaje.conductor else None,
        "convenio": viaje.convenio.cliente_nombre if viaje.convenio else None,
        "metodo": MetodoPago(pago.metodo).label if pago else None,
        "monto": pago.monto if pago else None,
        "forzado": forzado,
        "calificacion": calificacion.puntaje if calificacion else None,
    }


def _totales_historial(viajes) -> dict:
    montos = viajes.filter(pago__isnull=False).values_list("pago__monto", flat=True)
    return {"id": viajes.count(), "monto": sum(montos)}


def contingencia(empresa_id: int, filtros: dict) -> tuple[list, dict]:
    """Reservas de contingencia según el día de recogida real, por folio. «Sin turno» si no se encontró."""
    viajes = (
        _por_recogida(empresa_id, filtros)
        .filter(canal=Canal.CONTINGENCIA)
        .select_related("conductor__usuario", "pago")
        .order_by("folio_contingencia")
    )
    autores = dict(
        Auditoria.objects.filter(
            entidad=Entidad.VIAJE, accion="RESERVA_CONTINGENCIA", entidad_id__in=[v.pk for v in viajes]
        ).values_list("entidad_id", "usuario__nombre")
    )
    filas = []
    for viaje in viajes:
        pago = getattr(viaje, "pago", None)
        filas.append(
            {
                "folio": viaje.folio_contingencia,
                "id": viaje.pk,
                "recogida": viaje.recogida_en,
                "resultado": viaje.get_estado_display(),
                "conductor": viaje.conductor.usuario.nombre if viaje.conductor else None,
                "turno": f"Turno {viaje.turno_id}" if viaje.turno_id else "Sin turno",
                "metodo": pago.get_metodo_display() if pago else None,
                "monto": pago.monto if pago else None,
                "ingresado_por": autores.get(viaje.pk),
                "ingresado_en": viaje.creado_en,
            }
        )
    sin_turno = sum(1 for f in filas if f["conductor"] and f["turno"] == "Sin turno")
    return filas, {
        "folio": f"Total, {len(filas)} folios",
        "turno": f"{sin_turno} sin turno",
        "monto": sum(f["monto"] or 0 for f in filas),
    }


CALCULOS = {
    "liquidacion": liquidacion,
    "facturacion": facturacion,
    "cancelaciones": cancelaciones,
    "contingencia": contingencia,
}


def _texto_csv(valor, tipo: str) -> str:
    if valor is None:
        return ""
    if tipo == "fecha" and isinstance(valor, date):
        return valor.strftime("%d-%m-%Y")
    if tipo == "fecha_hora" and isinstance(valor, datetime):
        return timezone.localtime(valor).strftime("%d-%m-%Y %H:%M")
    if tipo == "porcentaje":
        return f"{valor}".replace(".", ",")
    if isinstance(valor, bool | int | float):
        return str(valor)
    texto = str(valor)
    # Un nombre como «=HYPERLINK(...)» no debe ejecutarse al abrir el archivo en una planilla.
    return f"'{texto}" if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def armar_csv(columnas: list, filas, totales: dict) -> str:
    salida = io.StringIO()
    salida.write("﻿")  # Excel reconoce el UTF-8.
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow([c["titulo"] for c in columnas])
    for fila in filas:
        escritor.writerow([_texto_csv(fila.get(c["clave"]), c["tipo"]) for c in columnas])
    escritor.writerow([_texto_csv(totales.get(c["clave"]), c["tipo"]) for c in columnas])
    return salida.getvalue()


PARAMETROS = [
    OpenApiParameter("desde", OpenApiTypes.DATE, description="Hoy si no se indica"),
    OpenApiParameter("hasta", OpenApiTypes.DATE, description="Hoy si no se indica"),
    OpenApiParameter("conductor", OpenApiTypes.INT),
    OpenApiParameter("convenio", OpenApiTypes.INT),
]
TIPO = OpenApiParameter(
    "tipo", str, OpenApiParameter.PATH, enum=list(COLUMNAS), description="Reporte que se pide"
)


class _VistaReporte(APIView):
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]

    def _filtros(self, request, tipo: str) -> dict:
        if tipo not in COLUMNAS:
            raise Http404
        entrada = ParametrosSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        return entrada.validated_data


class ReporteView(_VistaReporte):
    @extend_schema(
        tags=["reportes"],
        summary="Reporte operativo",
        parameters=[TIPO, *PARAMETROS, OpenApiParameter("page", OpenApiTypes.INT)],
        responses=ReporteSerializer,
    )
    def get(self, request, tipo):
        filtros = self._filtros(request, tipo)
        empresa_id = request.user.empresa_id
        siguiente = anterior = None
        if tipo == "historial":
            viajes = _consulta_historial(empresa_id, filtros)
            paginador = PageNumberPagination()
            filas = [_fila_historial(v) for v in paginador.paginate_queryset(viajes, request, self)]
            totales = _totales_historial(viajes)
            cuenta, siguiente, anterior = (
                totales["id"],
                paginador.get_next_link(),
                paginador.get_previous_link(),
            )
        else:
            filas, totales = CALCULOS[tipo](empresa_id, filtros)
            cuenta = len(filas)
        return Response(
            {
                "columnas": COLUMNAS[tipo],
                "filas": filas,
                "totales": totales,
                "count": cuenta,
                "next": siguiente,
                "previous": anterior,
            }
        )


class ReporteCsvView(_VistaReporte):
    @extend_schema(
        tags=["reportes"],
        summary="Exportar el reporte a CSV",
        parameters=[TIPO, *PARAMETROS],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
        description="Con los mismos filtros y columnas, sin paginar y con los totales en la última fila.",
    )
    def get(self, request, tipo):
        filtros = self._filtros(request, tipo)
        empresa_id = request.user.empresa_id
        if tipo == "historial":
            viajes = _consulta_historial(empresa_id, filtros)
            filas, totales = map(_fila_historial, viajes.iterator(chunk_size=500)), _totales_historial(viajes)
        else:
            filas, totales = CALCULOS[tipo](empresa_id, filtros)
        respuesta = HttpResponse(
            armar_csv(COLUMNAS[tipo], filas, totales), content_type="text/csv; charset=utf-8"
        )
        nombre = f"{tipo}-{filtros['desde'].isoformat()}-{filtros['hasta'].isoformat()}.csv"
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return respuesta


class OpcionesReporteView(_VistaReporte):
    @extend_schema(
        tags=["reportes"], summary="Conductores y convenios para los filtros", responses=OpcionesSerializer
    )
    def get(self, request):
        empresa_id = request.user.empresa_id
        conductores = Conductor.objects.filter(usuario__empresa_id=empresa_id).select_related("usuario")
        convenios = Convenio.objects.filter(empresa_id=empresa_id)
        return Response(
            {
                "conductores": sorted(
                    ({"id": c.pk, "nombre": c.usuario.nombre} for c in conductores), key=lambda o: o["nombre"]
                ),
                "convenios": [
                    {"id": c.pk, "nombre": c.cliente_nombre} for c in convenios.order_by("cliente_nombre")
                ],
            }
        )
