/**
 * Application entry point.
 *
 * Initializes Vue app with:
 * - Pinia for state management
 * - Vue Router for navigation
 * - Vue I18n for internationalization
 */

import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";
import i18n from "./locales";

import "./assets/styles/main.css";

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(i18n);

app.mount("#app");

// Cloudflare Web Analytics: load beacon only when token is configured.
// The token is empty in local development and set via render.yaml in production.
const cfToken = import.meta.env.VITE_CF_ANALYTICS_TOKEN;
if (cfToken) {
  const script = document.createElement("script");
  script.defer = true;
  script.src = "https://static.cloudflareinsights.com/beacon.min.js";
  script.dataset.cfBeacon = JSON.stringify({ token: cfToken });
  document.body.appendChild(script);
}
