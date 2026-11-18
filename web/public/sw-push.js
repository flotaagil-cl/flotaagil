/* HU-65 (CC-19, DC-62): service worker de los avisos del viaje por Web Push. Solo muestra la notificación que
   envía el servidor (título, texto y la página del viaje) y abre esa página al tocarla. No guarda nada. */

self.addEventListener('push', (evento) => {
  let datos = {};
  try {
    datos = evento.data ? evento.data.json() : {};
  } catch {
    datos = { cuerpo: evento.data ? evento.data.text() : '' };
  }
  evento.waitUntil(
    self.registration.showNotification(datos.titulo || 'Tu viaje', {
      body: datos.cuerpo || '',
      data: { url: datos.url || '/mis-viajes' },
      tag: datos.url || 'flotaagil-viaje',
    }),
  );
});

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const url = new URL(evento.notification.data?.url || '/mis-viajes', self.location.origin).href;
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ventanas) => {
      const abierta = ventanas.find((ventana) => ventana.url === url);
      return abierta ? abierta.focus() : self.clients.openWindow(url);
    }),
  );
});
