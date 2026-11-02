// Type declarations for the VITE_* environment variables this app reads.
// Merges with Vite's built-in ImportMetaEnv type.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
