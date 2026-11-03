import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'cl.flotaagil.conductor',
  appName: 'FlotaÁgil Conductor',
  webDir: 'dist',
  plugins: {
    // fetch nativo: la API no necesita CORS para la app y una URL http de desarrollo no choca con el origen
    // https://localhost del WebView. En release la URL debe ser https (el tráfico sin cifrar solo se permite en
    // los builds de depuración, android/app/src/debug/AndroidManifest.xml).
    CapacitorHttp: { enabled: true },
  },
};

export default config;
