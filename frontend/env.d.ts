/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_API_VERSION: string;
  readonly VITE_CF_ANALYTICS_TOKEN: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
