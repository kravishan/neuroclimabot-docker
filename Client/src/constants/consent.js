/**
 * Consent Management Constants
 * Defines consent types, storage keys, and default values
 */

// Consent Types
export const CONSENT_TYPES = {
  ESSENTIAL: 'essential',
  ANALYTICS: 'analytics'
}

// Consent Storage Key
export const CONSENT_STORAGE_KEY = 'neuroclima_consent_preferences'

// Consent Version (increment when consent policy changes)
export const CONSENT_VERSION = '1.0.0'

// Default Consent State (Analytics opt-out by default = on)
export const DEFAULT_CONSENT = {
  version: CONSENT_VERSION,
  timestamp: null,
  preferences: {
    [CONSENT_TYPES.ESSENTIAL]: true,  // Always required
    [CONSENT_TYPES.ANALYTICS]: true   // Default: ON (opt-out model)
  }
}

// Consent Category Descriptions
export const CONSENT_CATEGORIES = {
  [CONSENT_TYPES.ESSENTIAL]: {
    nameKey: 'consent.essential.name',
    descriptionKey: 'consent.essential.description',
    required: true,
    alwaysOn: true
  },
  [CONSENT_TYPES.ANALYTICS]: {
    nameKey: 'consent.analytics.name',
    descriptionKey: 'consent.analytics.description',
    required: false,
    alwaysOn: false
  }
}
