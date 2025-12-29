export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
  { code: 'el', name: 'Greek', nativeName: 'Ελληνικά' }
]

export const DEFAULT_LANGUAGE = import.meta.env.VITE_DEFAULT_LANGUAGE || 'en'

export const DIFFICULTY_LEVELS = [
  { value: 'low', label: 'easyReading' },
  { value: 'high', label: 'advancedReading' }
]