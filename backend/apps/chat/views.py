"""API del chat de trabajo (HU-61, HU-62): las mismas rutas para el panel y la app del conductor.

Un registro de otra empresa, o una conversación que el usuario no puede leer, responde 404 (RN-13).
"""

from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.auditoria.models import Entidad
from apps.auditoria.servicios import registrar
from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol, Usuario

from . import servicios
from .models import Conversacion, Mensaje, Participante, TipoConversacion
from .permisos import ROLES_PERSONAL, es_equipo, puede_escribir, visibles
from .serializers import (
    ConversacionChatSerializer,
    GrupoSerializer,
    IntegranteSerializer,
    LeidoSerializer,
    MensajeChatSerializer,
    NuevoDirectoSerializer,
    NuevoGrupoSerializer,
    NuevoMensajeSerializer,
    PaginaMensajesSerializer,
    PersonaChatSerializer,
)

T = TipoConversacion
POR_PAGINA = 30
DelPersonal = con_roles(*ROLES_PERSONAL)


class AntispamChat(UserRateThrottle):
    """Límite moderado de mensajes por usuario (CC-19); leer no cuenta."""

    scope = "chat"

    def allow_request(self, request, view):
        return request.method != "POST" or super().allow_request(request, view)


def _con_contadores(usuario, conversaciones):
    mi_leido = Participante.objects.filter(conversacion=OuterRef("pk"), usuario=usuario).values(
        "ultimo_leido_id"
    )[:1]
    no_leidos = (
        Mensaje.objects.filter(conversacion=OuterRef("pk"), pk__gt=OuterRef("mi_leido"))
        .exclude(autor=usuario)
        .order_by()
        .values("conversacion")
        .annotate(c=Count("pk"))
        .values("c")
    )
    return (
        conversaciones.select_related("conductor__usuario")
        .prefetch_related("participantes__usuario")
        .annotate(mi_leido=Coalesce(Subquery(mi_leido), 0))
        .annotate(no_leidos=Coalesce(Subquery(no_leidos), 0))
        .order_by(F("ultimo_mensaje_en").desc(nulls_last=True), "pk")
    )


def _datos(usuario, conversaciones) -> list[dict]:
    conversaciones = list(conversaciones)
    ultimos = {
        m.conversacion_id: m
        for m in Mensaje.objects.filter(conversacion__in=conversaciones)
        .order_by("conversacion_id", "-pk")
        .distinct("conversacion_id")
        .select_related("autor")
    }
    datos = []
    for c in conversaciones:
        ultimo = ultimos.get(c.pk)
        datos.append(
            {
                "id": c.pk,
                "tipo": c.tipo,
                "titulo": servicios.titulo(c, usuario),
                "no_leidos": c.no_leidos,
                "ultimo": None
                if ultimo is None
                else {
                    "texto": ultimo.texto,
                    "autor": servicios.nombre_autor(ultimo, c, usuario),
                    "creado_en": ultimo.creado_en,
                },
                "ultimo_mensaje_en": c.ultimo_mensaje_en,
                "puede_gestionar": c.tipo == T.GRUPO,
                "puede_borrar": c.tipo == T.GRUPO
                and (c.creado_por_id == usuario.pk or usuario.rol == Rol.ADMINISTRADOR),
            }
        )
    return datos


def _conversacion(request, pk) -> Conversacion:
    return get_object_or_404(visibles(request.user).select_related("conductor__usuario"), pk=pk)


class ConversacionesView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(
        responses=ConversacionChatSerializer(many=True), summary="Mis conversaciones con no leídos"
    )
    def get(self, request):
        usuario = request.user
        conversaciones = visibles(usuario)
        if es_equipo(usuario):
            servicios.asegurar_centrales(usuario.empresa_id)
            conversaciones = conversaciones.filter(~Q(tipo=T.CENTRAL) | Q(conductor__usuario__activo=True))
        elif usuario.rol == Rol.CONDUCTOR:
            servicios.asegurar_centrales(usuario.empresa_id)
        datos = _datos(usuario, _con_contadores(usuario, conversaciones))
        return Response(ConversacionChatSerializer(datos, many=True).data)


class ConversacionView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(responses=ConversacionChatSerializer, summary="Una conversación")
    def get(self, request, pk):
        conversaciones = _con_contadores(request.user, visibles(request.user).filter(pk=pk))
        datos = _datos(request.user, conversaciones)
        if not datos:
            raise NotFound()
        return Response(ConversacionChatSerializer(datos[0]).data)


class MensajesView(APIView):
    permission_classes = [DelPersonal]
    throttle_classes = [AntispamChat]

    @extend_schema(
        parameters=[
            OpenApiParameter("antes", int, required=False, description="Id del mensaje más antiguo cargado")
        ],
        responses=PaginaMensajesSerializer,
        summary="Historial paginado (los 30 anteriores a «antes»)",
    )
    def get(self, request, pk):
        conversacion = _conversacion(request, pk)
        mensajes = conversacion.mensajes.select_related("autor").order_by("-pk")
        antes = request.query_params.get("antes")
        if antes:
            if not antes.isdigit():
                raise ValidationError({"antes": "Debe ser un número."})
            mensajes = mensajes.filter(pk__lt=int(antes))
        pagina = list(mensajes[: POR_PAGINA + 1])
        datos = {
            "results": [
                servicios.datos_mensaje(m, conversacion, request.user) for m in reversed(pagina[:POR_PAGINA])
            ],
            "hay_mas": len(pagina) > POR_PAGINA,
            "leido_por_otros_hasta": servicios.leido_por_otros(conversacion, request.user),
        }
        return Response(PaginaMensajesSerializer(datos).data)

    @extend_schema(request=NuevoMensajeSerializer, responses={201: MensajeChatSerializer}, summary="Escribir")
    def post(self, request, pk):
        conversacion = _conversacion(request, pk)
        if not puede_escribir(request.user, conversacion):
            raise PermissionDenied("En esta conversación solo puedes leer.", code="solo_lectura")
        entrada = NuevoMensajeSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        mensaje = servicios.publicar(
            request.user,
            conversacion,
            entrada.validated_data["texto"],
            entrada.validated_data.get("rapida", ""),
        )
        datos = servicios.datos_mensaje(mensaje, conversacion, request.user)
        return Response(MensajeChatSerializer(datos).data, status=status.HTTP_201_CREATED)


class LeidoView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(request=LeidoSerializer, responses={204: None}, summary="Marcar leído hasta un mensaje")
    def post(self, request, pk):
        conversacion = _conversacion(request, pk)
        entrada = LeidoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        ultimo = conversacion.mensajes.order_by("-pk").values_list("pk", flat=True).first() or 0
        servicios.marcar_leido(request.user, conversacion, min(entrada.validated_data["hasta"], ultimo))
        return Response(status=status.HTTP_204_NO_CONTENT)


def _personal(usuario):
    return Usuario.objects.filter(empresa_id=usuario.empresa_id, activo=True, rol__in=ROLES_PERSONAL)


class PersonalView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(
        responses=PersonaChatSerializer(many=True), summary="Personal de la empresa para directos y grupos"
    )
    def get(self, request):
        personas = (
            _personal(request.user)
            .exclude(pk=request.user.pk)
            .order_by("nombre")
            .values("id", "nombre", "rol")
        )
        return Response(PersonaChatSerializer(personas, many=True).data)


class DirectosView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(
        request=NuevoDirectoSerializer,
        responses={200: ConversacionChatSerializer, 201: ConversacionChatSerializer},
    )
    def post(self, request):
        entrada = NuevoDirectoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        otro = (
            _personal(request.user)
            .exclude(pk=request.user.pk)
            .filter(pk=entrada.validated_data["usuario"])
            .first()
        )
        if otro is None:
            raise NotFound("Esa persona no está en el personal de tu empresa.")
        conversacion, creado = servicios.directo(request.user, otro)
        if creado:
            servicios.avisar_cambio(conversacion)
        datos = _datos(
            request.user, _con_contadores(request.user, Conversacion.objects.filter(pk=conversacion.pk))
        )
        return Response(ConversacionChatSerializer(datos[0]).data, status=201 if creado else 200)


def _integrantes(usuario, ids) -> list[Usuario]:
    personas = list(_personal(usuario).filter(pk__in=set(ids)))
    if len(personas) != len(set(ids)):
        raise ValidationError(
            {"integrantes": "Solo puedes agregar personal activo de tu empresa."}, code="integrante_invalido"
        )
    return personas


def _datos_grupo(grupo: Conversacion) -> dict:
    return {
        "id": grupo.pk,
        "nombre": grupo.nombre,
        "integrantes": [
            {"id": p.usuario_id, "nombre": p.usuario.nombre, "rol": p.usuario.rol}
            for p in grupo.participantes.select_related("usuario").order_by("usuario__nombre")
        ],
        "creado_por": grupo.creado_por.nombre if grupo.creado_por_id else None,
        "creado_en": grupo.creado_en,
        "ultimo_mensaje_en": grupo.ultimo_mensaje_en,
    }


class GruposView(APIView):
    permission_classes = [DelPersonal]

    @extend_schema(request=NuevoGrupoSerializer, responses={201: GrupoSerializer}, summary="Crear un grupo")
    def post(self, request):
        entrada = NuevoGrupoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        ids = set(entrada.validated_data["ids_integrantes"]) - {request.user.pk}
        if not ids:
            raise ValidationError(
                {"ids_integrantes": "Agrega al menos a otra persona."}, code="sin_integrantes"
            )
        personas = _integrantes(request.user, ids)
        with transaction.atomic():
            grupo = Conversacion.objects.create(
                empresa_id=request.user.empresa_id,
                tipo=T.GRUPO,
                nombre=entrada.validated_data["nombre"],
                creado_por=request.user,
            )
            Participante.objects.bulk_create(
                [Participante(conversacion=grupo, usuario=u) for u in [request.user, *personas]]
            )
            servicios.avisar_cambio(grupo)
        return Response(GrupoSerializer(_datos_grupo(grupo)).data, status=status.HTTP_201_CREATED)


class GestionGrupo:
    """Los integrantes gestionan su grupo; el administrador modera cualquiera sin leerlo (solo metadatos)."""

    def grupo(self, request, pk) -> tuple[Conversacion, bool]:
        grupo = (
            Conversacion.objects.filter(
                empresa_id=request.user.empresa_id, tipo=T.GRUPO, borrado_en__isnull=True
            )
            .select_related("creado_por")
            .filter(pk=pk)
            .first()
        )
        participa = grupo is not None and grupo.participantes.filter(usuario=request.user).exists()
        if grupo is None or not (participa or request.user.rol == Rol.ADMINISTRADOR):
            raise NotFound()
        return grupo, participa

    def auditar(self, request, grupo, accion, datos_previos, participa):
        """Todo borrado queda en auditoría; los demás cambios, cuando los hace el administrador sin estar."""
        if accion == "BORRAR_GRUPO" or not participa:
            registrar(
                usuario=request.user,
                entidad=Entidad.CONVERSACION,
                entidad_id=grupo.pk,
                accion=accion if participa else f"MODERAR_{accion}",
                datos_previos=datos_previos,
            )


class GrupoView(GestionGrupo, APIView):
    permission_classes = [DelPersonal]

    @extend_schema(responses=GrupoSerializer, summary="Datos del grupo (nombre, integrantes y fechas)")
    def get(self, request, pk):
        grupo, _ = self.grupo(request, pk)
        return Response(GrupoSerializer(_datos_grupo(grupo)).data)

    @extend_schema(request=GrupoSerializer, responses=GrupoSerializer, summary="Renombrar el grupo")
    def patch(self, request, pk):
        grupo, participa = self.grupo(request, pk)
        entrada = GrupoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        anterior = grupo.nombre
        grupo.nombre = entrada.validated_data["nombre"]
        grupo.save(update_fields=["nombre"])
        self.auditar(request, grupo, "RENOMBRAR_GRUPO", {"nombre": anterior}, participa)
        servicios.avisar_cambio(grupo)
        return Response(GrupoSerializer(_datos_grupo(grupo)).data)

    @extend_schema(responses={204: None}, summary="Borrar el grupo (su creador o el administrador)")
    def delete(self, request, pk):
        grupo, participa = self.grupo(request, pk)
        if grupo.creado_por_id != request.user.pk and request.user.rol != Rol.ADMINISTRADOR:
            raise PermissionDenied(
                "Solo quien creó el grupo o el administrador pueden borrarlo.", code="no_es_creador"
            )
        with transaction.atomic():
            self.auditar(request, grupo, "BORRAR_GRUPO", {"nombre": grupo.nombre}, participa)
            servicios.borrar_grupo(grupo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class IntegrantesView(GestionGrupo, APIView):
    permission_classes = [DelPersonal]

    @extend_schema(
        request=IntegranteSerializer, responses={201: GrupoSerializer}, summary="Agregar a un integrante"
    )
    def post(self, request, pk):
        grupo, participa = self.grupo(request, pk)
        if not participa:
            # El administrador que no está en el grupo no puede agregarse ni agregar a otros (DC-64).
            raise PermissionDenied("Solo los integrantes agregan personas al grupo.", code="no_es_integrante")
        entrada = IntegranteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        (persona,) = _integrantes(request.user, [entrada.validated_data["usuario"]])
        Participante.objects.get_or_create(conversacion=grupo, usuario=persona)
        servicios.avisar_cambio(grupo)
        return Response(GrupoSerializer(_datos_grupo(grupo)).data, status=status.HTTP_201_CREATED)


class IntegranteView(GestionGrupo, APIView):
    permission_classes = [DelPersonal]

    @extend_schema(responses={204: None}, summary="Quitar a un integrante o salir del grupo")
    def delete(self, request, pk, usuario_id):
        grupo, participa = self.grupo(request, pk)
        propio = usuario_id == request.user.pk
        if not propio and grupo.creado_por_id != request.user.pk and request.user.rol != Rol.ADMINISTRADOR:
            raise PermissionDenied(
                "Solo quien creó el grupo o el administrador quitan integrantes.", code="no_es_creador"
            )
        borrados, _ = Participante.objects.filter(conversacion=grupo, usuario_id=usuario_id).delete()
        if not borrados:
            raise NotFound()
        self.auditar(request, grupo, "QUITAR_INTEGRANTE", {"usuario": usuario_id}, participa)
        servicios.avisar_cambio(grupo, ids_extra=[usuario_id])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModeracionView(APIView):
    """Solo metadatos: el administrador no lee los mensajes de grupos ni directos."""

    permission_classes = [con_roles(Rol.ADMINISTRADOR)]

    @extend_schema(responses=GrupoSerializer(many=True), summary="Grupos de la empresa (solo metadatos)")
    def get(self, request):
        grupos = (
            Conversacion.objects.filter(
                empresa_id=request.user.empresa_id, tipo=T.GRUPO, borrado_en__isnull=True
            )
            .select_related("creado_por")
            .order_by("nombre")
        )
        return Response(GrupoSerializer([_datos_grupo(g) for g in grupos], many=True).data)
