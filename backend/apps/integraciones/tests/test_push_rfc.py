"""DC-67: cifrado y VAPID propios de Web Push contra los ejemplos oficiales de los RFC 8291 y 8292."""

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.test import override_settings

from apps.integraciones import push

# RFC 8291, sección 5 y apéndice A (valores en base64url, sin los saltos de línea del RFC).
RFC8291 = {
    "texto": b"When I grow up, I want to be a watermelon",
    "auth": "BTBZMqHH6r4Tts7J_aSIgg",
    "ua_publica": "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
    "ua_privada": "q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94",
    "as_publica": "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8",
    "as_privada": "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw",
    "sal": "DGv6ra1nlYgDCS1FRnbzlw",
    "cek": "oIhVW04MRdy2XN9CiKLxTg",
    "nonce": "4h_95klXJ5E_qnoN",
    "cuerpo": (
        "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27ml"
        "mlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPT"
        "pK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
    ),
}

# RFC 8292, sección 2.4: encabezado Authorization del ejemplo.
RFC8292_TOKEN = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJhdWQiOiJodHRwczovL3B1c2guZXhhbXBsZS5uZXQiLCJleHAiOjE0NTM1MjM3Njgs"
    "InN1YiI6Im1haWx0bzpwdXNoQGV4YW1wbGUuY29tIn0.i3CYb7t4xfxCDquptFOepC9GAu_HLGkMlMuCGSK2rpiUfnK9ojFwDXb1JrErtm"
    "ysazNjjvW2L9OkSSHzvoD1oA"
)
RFC8292_K = "BA1Hxzyi1RUM1b5wjxsn7nGxAszw2u61m164i3MrAIxHF6YK5h4SDYic-dRuU_RCPCfA5aq9ojSwk5Y2EmClBPs"


def _privada(texto):
    return ec.derive_private_key(int.from_bytes(push.desde_b64(texto), "big"), ec.SECP256R1())


def _verificar_vapid(encabezado, *, verificar_exp=True):
    """Lo que hace el servicio push (RFC 8292 §3): separa t y k y valida la firma ES256 con k."""
    esquema, credenciales = encabezado.split(" ", 1)
    assert esquema == "vapid"
    partes = dict(p.strip().split("=", 1) for p in credenciales.split(","))
    publica = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), push.desde_b64(partes["k"]))
    assert jwt.get_unverified_header(partes["t"])["alg"] == "ES256"
    return jwt.decode(
        partes["t"],
        publica,
        algorithms=["ES256"],
        audience="https://push.example.net",
        options={"verify_exp": verificar_exp},
    )


def test_rfc8291_mismo_cuerpo_que_el_ejemplo():
    cuerpo = push.cifrar(
        RFC8291["texto"],
        RFC8291["ua_publica"],
        RFC8291["auth"],
        sal=push.desde_b64(RFC8291["sal"]),
        efimera=_privada(RFC8291["as_privada"]),
    )
    assert push.b64(cuerpo) == RFC8291["cuerpo"]
    # Encabezado de 86 octetos: sal, tamaño de registro 4096 y la clave pública del servidor.
    assert len(cuerpo) - len(RFC8291["texto"]) - 1 - 16 == 86
    assert push.b64(cuerpo[21:86]) == RFC8291["as_publica"]


def test_rfc8291_el_navegador_lo_descifra_con_la_cek_y_el_nonce_del_apendice_a():
    cuerpo = push.desde_b64(RFC8291["cuerpo"])
    cek, nonce = push.desde_b64(RFC8291["cek"]), push.desde_b64(RFC8291["nonce"])
    claro = AESGCM(cek).decrypt(nonce, cuerpo[86:], None)
    assert claro == RFC8291["texto"] + b"\x02"


def test_rfc8291_sal_y_clave_efimera_nuevas_en_cada_envio():
    a = push.cifrar(b"x", RFC8291["ua_publica"], RFC8291["auth"])
    b = push.cifrar(b"x", RFC8291["ua_publica"], RFC8291["auth"])
    assert a[:16] != b[:16] and a[21:86] != b[21:86]


def test_rfc8292_el_ejemplo_valida_con_el_mismo_verificador():
    reclamos = _verificar_vapid(f"vapid t={RFC8292_TOKEN}, k={RFC8292_K}", verificar_exp=False)
    esperado = {"aud": "https://push.example.net", "exp": 1453523768, "sub": "mailto:push@example.com"}
    assert reclamos == esperado


@override_settings(
    WEBPUSH_VAPID_PUBLICA=RFC8291["as_publica"],
    WEBPUSH_VAPID_PRIVADA=RFC8291["as_privada"],
    WEBPUSH_CONTACTO="mailto:push@example.com",
)
def test_rfc8292_nuestro_encabezado_tiene_la_misma_forma_y_valida():
    ahora = 1_700_000_000
    endpoint = "https://push.example.net/p/JzLQ3raZJfFBR0aqvOMsLrt54w4rJUsV"
    encabezado = push.encabezado_vapid(endpoint, ahora=ahora)
    assert encabezado.endswith(f", k={RFC8291['as_publica']}")
    reclamos = _verificar_vapid(encabezado, verificar_exp=False)
    assert reclamos["sub"] == "mailto:push@example.com"
    # RFC 8292 §2: exp a no más de 24 horas.
    assert ahora < reclamos["exp"] <= ahora + 24 * 3600
