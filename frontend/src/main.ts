/**
 * Application entry point.
 *
 * Initializes Vue app with:
 * - Pinia for state management
 * - Vue Router for navigation
 * - Vue I18n for internationalization
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import i18n from './locales'

import './assets/styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')
