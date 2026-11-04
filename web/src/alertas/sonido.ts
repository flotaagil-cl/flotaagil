/**
 * Alerta sonora de vuelos (HU-28): dos tonos cortos, sin archivos. El navegador puede bloquear el audio hasta que
 * el usuario interactúe con la página; en ese caso queda la alerta visual, que es la que no se puede perder.
 */

export function sonarAlerta(): void {
  const Contexto = globalThis.AudioContext;
  if (!Contexto) return;
  try {
    const audio = new Contexto();
    [0, 0.25].forEach((desde) => {
      const tono = audio.createOscillator();
      const volumen = audio.createGain();
      tono.frequency.value = 880;
      volumen.gain.value = 0.15;
      tono.connect(volumen);
      volumen.connect(audio.destination);
      tono.start(audio.currentTime + desde);
      tono.stop(audio.currentTime + desde + 0.18);
    });
    void audio.resume().catch(() => {});
    setTimeout(() => void audio.close().catch(() => {}), 1000);
  } catch {
    // Sin audio disponible: queda la alerta visual.
  }
}
