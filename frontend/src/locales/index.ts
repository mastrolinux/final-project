/**
 * Locale configuration and i18n setup.
 */

import { createI18n } from 'vue-i18n'

import en from './en.json'
import es from './es.json'
import zh from './zh.json'
import ar from './ar.json'
import it from './it.json'

export type SupportedLocale = 'en' | 'it' | 'es' | 'zh' | 'ar'

export const SUPPORTED_LOCALES: SupportedLocale[] = ['en', 'it', 'es', 'zh', 'ar']

export const LOCALE_NAMES: Record<SupportedLocale, string> = {
  en: 'English',
  it: 'Italiano',
  es: 'Espanol',
  zh: '中文',
  ar: 'العربية'
}

/**
 * Detect user's preferred locale from browser settings.
 */
function detectLocale(): SupportedLocale {
  const browserLang = navigator.language.split('-')[0]
  if (SUPPORTED_LOCALES.includes(browserLang as SupportedLocale)) {
    return browserLang as SupportedLocale
  }
  return 'en'
}

/**
 * Get stored locale or detect from browser.
 */
function getInitialLocale(): SupportedLocale {
  const stored = localStorage.getItem('locale')
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale
  }
  return detectLocale()
}

export const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    it,
    es,
    zh,
    ar
  }
})

/**
 * Change the current locale and persist to localStorage.
 */
export function setLocale(locale: SupportedLocale): void {
  i18n.global.locale.value = locale
  localStorage.setItem('locale', locale)
  document.documentElement.lang = locale
  document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'
}

export default i18n
