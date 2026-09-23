/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend base URL; defaults to the Railway deployment. */
  readonly VITE_API_BASE_URL?: string;
  /** Local-only: skips the sign-in screen. Never set on a public deploy. */
  readonly VITE_API_KEY?: string;
}
