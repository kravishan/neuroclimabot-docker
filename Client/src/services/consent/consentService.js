/**
 * Consent Service
 * Manages user consent preferences in localStorage
 */

import {
  CONSENT_STORAGE_KEY,
  DEFAULT_CONSENT,
  CONSENT_TYPES,
  CONSENT_VERSION
} from '@/constants/consent'

class ConsentService {
  /**
   * Get current consent preferences from localStorage
   * @returns {Object} Consent preferences object
   */
  getConsent() {
    try {
      const stored = localStorage.getItem(CONSENT_STORAGE_KEY)
      if (!stored) {
        return null // No consent given yet
      }

      const consent = JSON.parse(stored)

      // Check if consent version matches (for policy updates)
      if (consent.version !== CONSENT_VERSION) {
        console.log('Consent version mismatch - requesting new consent')
        return null
      }

      return consent
    } catch (error) {
      console.error('Error reading consent preferences:', error)
      return null
    }
  }

  /**
   * Save consent preferences to localStorage
   * @param {Object} preferences - Consent preferences object
   */
  setConsent(preferences) {
    try {
      const consent = {
        version: CONSENT_VERSION,
        timestamp: new Date().toISOString(),
        preferences: {
          [CONSENT_TYPES.ESSENTIAL]: true, // Always true
          [CONSENT_TYPES.ANALYTICS]: preferences[CONSENT_TYPES.ANALYTICS] ?? true
        }
      }

      localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consent))
      console.log('Consent preferences saved:', consent)

      // Dispatch custom event for other components to listen
      window.dispatchEvent(new CustomEvent('consentChanged', { detail: consent }))

      return consent
    } catch (error) {
      console.error('Error saving consent preferences:', error)
      return null
    }
  }

  /**
   * Check if user has given consent for a specific type
   * @param {string} type - Consent type (essential, analytics)
   * @returns {boolean} True if consent given
   */
  hasConsent(type) {
    const consent = this.getConsent()

    // If no consent given yet, return default (true for opt-out model)
    if (!consent) {
      return DEFAULT_CONSENT.preferences[type]
    }

    return consent.preferences[type] === true
  }

  /**
   * Check if user has been asked for consent
   * @returns {boolean} True if consent has been set
   */
  hasConsentBeenSet() {
    return this.getConsent() !== null
  }

  /**
   * Accept all consent types
   */
  acceptAll() {
    return this.setConsent({
      [CONSENT_TYPES.ESSENTIAL]: true,
      [CONSENT_TYPES.ANALYTICS]: true
    })
  }

  /**
   * Reject optional consent types (keep only essential)
   */
  rejectOptional() {
    return this.setConsent({
      [CONSENT_TYPES.ESSENTIAL]: true,
      [CONSENT_TYPES.ANALYTICS]: false
    })
  }

  /**
   * Reset consent (for testing/debugging)
   */
  resetConsent() {
    try {
      localStorage.removeItem(CONSENT_STORAGE_KEY)
      console.log('Consent preferences reset')
      window.dispatchEvent(new CustomEvent('consentChanged', { detail: null }))
    } catch (error) {
      console.error('Error resetting consent:', error)
    }
  }

  /**
   * Get consent metadata for API requests
   * @returns {Object} Consent metadata
   */
  getConsentMetadata() {
    const consent = this.getConsent()
    return {
      consent_given: this.hasConsentBeenSet(),
      analytics_consent: this.hasConsent(CONSENT_TYPES.ANALYTICS),
      consent_version: consent?.version || null,
      consent_timestamp: consent?.timestamp || null
    }
  }
}

// Export singleton instance
export const consentService = new ConsentService()
