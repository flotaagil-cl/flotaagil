// DC-67: prueba de punta a punta de Web Push en Chrome sobre localhost.
//
// Uso:  node scripts/e2e-push.mjs
//
// Necesita el web en E2E_URL (por defecto http://localhost:5173), el backend y el worker con las claves VAPID
// de desarrollo en backend/.env, la cuenta sintética de HU-64 (npm run capturas -- HU-64) y DATOS_DEMO_PASSWORD.
// Abre Chrome con un perfil temporal (Web Push no funciona en incógnito), el pasajero acepta las notificaciones
// en «Tu viaje», el despachador cancela el viaje en el backend y se espera la notificación en el service worker.
// Deja docs/evidencias/DC-67/web-push-chrome-1440.png. No imprime claves.
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const URL_BASE = process.env.E2E_URL ?? "http://localhost:5173";
const CUENTA = "activa-hu64@correo.example";
const DESPACHO = "despacho@transportes-andes.example";

const NUEVO_VIAJE = [
  "from datetime import timedelta",
  "from django.utils import timezone",
  "from rest_framework.test import APIClient",
  "from apps.reservas.cuentas_pasajero import reservas_de",
  "from apps.reservas.models import CuentaPasajero",
  `cuenta = CuentaPasajero.objects.get(usuario__email="${CUENTA}")`,
  'viaje = reservas_de(cuenta).filter(estado="SOLICITADO").order_by("-pk").first()',
  "if viaje is None:  # como lo pediría el portal (con su límite por hora)",
  '    c = APIClient(HTTP_HOST="localhost")',
  "    c.force_authenticate(cuenta.usuario)",
  '    datos = {"origen_dir": "Av. Providencia 1234, Providencia", "destino_dir": "Plaza de Armas, Santiago",',
  '             "recogida_en": (timezone.now() + timedelta(hours=3)).isoformat(), "acepta_privacidad": True}',
  '    print(c.post("/api/mi-cuenta/solicitudes/", datos, format="json").data["id"])',
  "else:",
  "    print(viaje.pk)",
].join("\n");

const cancelar = (id) =>
  [
    "from apps.cuentas.models import Usuario",
    "from apps.reservas.models import Viaje",
    "from apps.reservas.servicios import cancelar_viaje",
    `u = Usuario.objects.get(email="${DESPACHO}")`,
    `v = cancelar_viaje(Viaje.objects.get(pk=${id}), motivo="Prueba de avisos Web Push (datos sintéticos)", usuario=u)`,
    "print(v.estado)",
  ].join("\n");

function shell(codigo) {
  return execFileSync(
    "docker",
    [
      "compose",
      "-f",
      join(RAIZ, "infra", "docker-compose.dev.yml"),
      "exec",
      "-T",
      "backend",
      "python",
      "manage.py",
      "shell",
      "-c",
      codigo,
    ],
    {
      encoding: "utf8",
    },
  )
    .trim()
    .split("\n")
    .at(-1);
}

async function main() {
  const clave = process.env.DATOS_DEMO_PASSWORD;
  if (!clave) throw new Error("Falta DATOS_DEMO_PASSWORD.");
  const viaje = shell(NUEVO_VIAJE);
  const perfil = mkdtempSync(join(tmpdir(), "flotaagil-push-"));
  const contexto = await chromium.launchPersistentContext(perfil, {
    channel: "chrome",
    headless: false,
    // Sin esto Chrome no conecta con su servicio push (FCM) y la suscripción falla.
    ignoreDefaultArgs: ["--disable-background-networking"],
    locale: "es-CL",
    timezoneId: "America/Santiago",
    viewport: { width: 1440, height: 900 },
  });
  try {
    // El pasajero acepta las notificaciones del sitio (lo que hace al tocar «Permitir»).
    await contexto.grantPermissions(["notifications"], { origin: URL_BASE });
    const pagina = contexto.pages()[0] ?? (await contexto.newPage());
    // Diagnóstico: el portal muestra un mensaje genérico; aquí queda el error real de la suscripción.
    const errores = [];
    pagina.on(
      "console",
      (m) => m.text().startsWith("[push]") && errores.push(m.text()),
    );
    await pagina.addInitScript(() => {
      const original = PushManager.prototype.subscribe;
      PushManager.prototype.subscribe = function (...args) {
        return original.apply(this, args).catch((error) => {
          console.error(`[push] ${error.name}: ${error.message}`);
          throw error;
        });
      };
    });
    await pagina.goto(`${URL_BASE}/login`);
    await pagina.getByLabel("Correo").fill(CUENTA);
    await pagina.getByLabel("Contraseña").fill(clave);
    await pagina.getByRole("button", { name: "Ingresar" }).click();
    await pagina.waitForURL((url) => url.pathname !== "/login", {
      timeout: 15000,
    });

    await pagina.goto(`${URL_BASE}/mis-viajes/${viaje}`);
    // El primer registro de Chrome con su servicio push tarda (~30 s).
    const suscrita = pagina.waitForResponse(
      (r) =>
        r.url().endsWith("/api/mi-cuenta/push/") &&
        r.request().method() === "POST",
      { timeout: 90000 },
    );
    suscrita.catch(() => {});
    const activar = pagina.getByRole("button", {
      name: "Activar avisos en este dispositivo",
    });
    await activar.waitFor({ timeout: 15000 }).catch(async () => {
      const avisos = await pagina
        .locator("main")
        .innerText()
        .catch(() => "");
      throw new Error(
        `Sin el botón de avisos en ${new URL(pagina.url()).pathname}:\n${avisos.slice(0, 600)}`,
      );
    });
    await activar.click();
    const falla = pagina
      .getByRole("alert")
      .filter({ hasText: "No pudimos activar los avisos" });
    const respuesta = await Promise.race([
      suscrita,
      falla.waitFor({ timeout: 90000 }).then(() => {
        throw new Error(
          `El portal no pudo suscribirse a Web Push: ${errores.join(" · ") || "sin detalle"}`,
        );
      }),
    ]);
    if (!respuesta.ok())
      throw new Error(`La suscripción respondió ${respuesta.status()}.`);
    await pagina.getByText("Te avisaremos en este dispositivo").waitFor();
    console.log(`ok   suscripción guardada (viaje ${viaje})`);

    console.log(`ok   el despachador cancela: ${shell(cancelar(viaje))}`);
    // Las notificaciones que mostró el service worker al recibir el push (hasta 90 s).
    let notificaciones = [];
    for (
      let intento = 0;
      intento < 90 && !notificaciones.length;
      intento += 1
    ) {
      if (intento) await pagina.waitForTimeout(1000);
      notificaciones = await pagina.evaluate(async () => {
        const registro =
          await navigator.serviceWorker.getRegistration("/sw-push.js");
        const lista = registro ? await registro.getNotifications() : [];
        return lista.map((n) => ({ titulo: n.title, cuerpo: n.body }));
      });
    }
    if (!notificaciones.length)
      throw new Error(
        "No llegó la notificación en 90 s (revisa el worker: enviar_push).",
      );
    console.log(
      `ok   notificación: «${notificaciones[0].titulo}» · ${notificaciones[0].cuerpo}`,
    );

    // Evidencia: la página del viaje ya cancelado y, encima, la notificación que mostró el service worker
    // (la del sistema operativo queda fuera de la página).
    await pagina.reload();
    await pagina.waitForLoadState("networkidle");
    await pagina.evaluate((n) => {
      const caja = document.createElement("aside");
      caja.setAttribute(
        "style",
        "position:fixed;top:16px;right:16px;z-index:9999;max-width:360px;padding:12px 16px;background:#fff;color:#123;border:1px solid #8aa;border-radius:12px;box-shadow:0 6px 24px #0003;font:14px system-ui",
      );
      caja.innerHTML =
        '<div style="font-size:12px;color:#567">Notificación recibida en Chrome (service worker, Web Push)</div>';
      const titulo = document.createElement("strong");
      titulo.textContent = n.titulo;
      const cuerpo = document.createElement("div");
      cuerpo.textContent = n.cuerpo;
      caja.append(titulo, cuerpo);
      document.body.append(caja);
    }, notificaciones[0]);
    const carpeta = join(RAIZ, "docs", "evidencias", "DC-67");
    mkdirSync(carpeta, { recursive: true });
    await pagina.screenshot({
      path: join(carpeta, "web-push-chrome-1440.png"),
    });
    console.log("ok   captura docs/evidencias/DC-67/web-push-chrome-1440.png");
  } finally {
    await contexto.close();
    rmSync(perfil, { recursive: true, force: true });
  }
}

await main();
