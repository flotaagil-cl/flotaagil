from django.urls import path

from . import views

urlpatterns = [
    path("conversaciones/", views.ConversacionesView.as_view(), name="chat-conversaciones"),
    path("conversaciones/<int:pk>/", views.ConversacionView.as_view(), name="chat-conversacion"),
    path("conversaciones/<int:pk>/mensajes/", views.MensajesView.as_view(), name="chat-mensajes"),
    path("conversaciones/<int:pk>/leido/", views.LeidoView.as_view(), name="chat-leido"),
    path("personal/", views.PersonalView.as_view(), name="chat-personal"),
    path("directos/", views.DirectosView.as_view(), name="chat-directos"),
    path("grupos/", views.GruposView.as_view(), name="chat-grupos"),
    path("grupos/<int:pk>/", views.GrupoView.as_view(), name="chat-grupo"),
    path("grupos/<int:pk>/integrantes/", views.IntegrantesView.as_view(), name="chat-integrantes"),
    path(
        "grupos/<int:pk>/integrantes/<int:usuario_id>/",
        views.IntegranteView.as_view(),
        name="chat-integrante",
    ),
    path("moderacion/grupos/", views.ModeracionView.as_view(), name="chat-moderacion"),
    path("viajes/<int:viaje_id>/", views.ViajeChatView.as_view(), name="chat-viaje"),
    path("viajes/<int:viaje_id>/lectura/", views.LecturaViajeView.as_view(), name="chat-viaje-lectura"),
    path("soporte/", views.SoporteView.as_view(), name="chat-soporte"),
]
