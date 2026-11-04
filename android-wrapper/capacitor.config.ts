import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'cz.dominik.microhelper',
  appName: 'Micro Helper',
  webDir: 'www',
  server: {
    url: 'https://micro-helper-ygeuyn.v2.appdeploy.ai/',
    cleartext: false
  },
  android: {
    allowMixedContent: false
  }
};

export default config;
