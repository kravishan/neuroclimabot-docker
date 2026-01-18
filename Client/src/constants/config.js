export const API_CONFIG = {
  // Use relative paths for production (works with Nginx Gateway)
  // Falls back to localhost for local development without gateway
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '/server',
  DOCUMENT_URL: import.meta.env.VITE_API_DOCUMENT_URL || '/processor',
  TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT) || 120000,
  ENDPOINTS: {
    CHAT_START: '/api/v1/chat/start',
    CHAT_CONTINUE: '/api/v1/chat/continue',
    SESSIONS: '/api/v1/chat/sessions',
    FEEDBACK: '/api/v1/feedback/submit',
    QUESTIONNAIRE_SUBMIT: '/api/v1/questionnaire/submit',
    QUESTIONNAIRE_STATS: '/api/v1/questionnaire/stats',
    HEALTH: '/api/v1/health/',
    GRAPH: '/api/v1/graph-viz/force-graph-visualization',
    // Admin endpoints (Server 1)
    ADMIN_LOGIN: '/api/v1/admin/login',
    ADMIN_STATS: '/api/v1/admin/stats',
    ADMIN_LOGS: '/api/v1/admin/logs',
    ADMIN_DOCUMENTS: '/api/v1/admin/documents',
    FEEDBACK_STATS: '/api/v1/feedback/stats',
    // External Services Health Checks
    TRANSLATE_HEALTH: '/translate/health',
    STP_HEALTH: '/stp/health',
    // Document processing endpoints (Server 2)
    DOC_PROCESS: '/process/document',
    DOC_BATCH_ALL: '/batch/process-all',
    DOC_BATCH_BUCKET: '/batch/process-bucket',
    DOC_TASKS: '/tasks',
    DOC_BUCKETS: '/minio/buckets',
    DOC_TRACKING: '/tracking/documents'
  }
}

export const APP_CONFIG = {
  NAME: import.meta.env.VITE_APP_NAME || 'Neuroclima Bot',
  VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
  ENVIRONMENT: import.meta.env.VITE_APP_ENVIRONMENT || 'development'
}

export const SESSION_CONFIG = {
  TIMEOUT_MINUTES: parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MINUTES) || 20,
  WARNING_MINUTES: parseInt(import.meta.env.VITE_INACTIVITY_WARNING_MINUTES) || 5,
  STORAGE_KEY: 'neuroclima_session_id'
}

export const FEATURE_FLAGS = {
  VOICE_MODEL: import.meta.env.VITE_ENABLE_VOICE_MODEL === 'true',
  GRAPH_VISUALIZATION: import.meta.env.VITE_ENABLE_GRAPH_VISUALIZATION === 'true',
  ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  ADMIN_DASHBOARD: import.meta.env.VITE_ENABLE_ADMIN_DASHBOARD !== 'false'
}

export const EXTERNAL_URLS = {
  FEEDBACK_FORM: import.meta.env.VITE_FEEDBACK_FORM_URL || '',
  DASHBOARD: import.meta.env.VITE_DASHBOARD_URL || './dashboard/user/index.html',
  UNIVERSITY_OULU: 'https://www.oulu.fi/en',
  UBICOMP: 'https://ubicomp.oulu.fi/',
  FCG: 'https://ubicomp.oulu.fi/research/fcg'
}

export const GRAPH_CONFIG = {
  DEFAULT_BUCKET: 'researchpapers',
  FORCE_SIMULATION: {
    CHARGE_STRENGTH: -300,
    LINK_DISTANCE: 300,
    ALPHA_DECAY: 0.0228,
    VELOCITY_DECAY: 0.4
  }
}

// Document Processing Configuration
export const DOCUMENT_CONFIG = {
  PROCESSABLE_EXTENSIONS: ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt'],
  DEFAULT_SEARCH_LIMIT: 10,
  DOCUMENTS_PER_PAGE: 10, // Number of documents to show per page
  BATCH_PROCESSING_OPTIONS: {
    SKIP_PROCESSED: true,
    INCLUDE_CHUNKING: true,
    INCLUDE_SUMMARIZATION: true,
    INCLUDE_GRAPHRAG: true,
    INCLUDE_STP: true // STP enabled by default
  },
  // API retry configuration
  RETRY_CONFIG: {
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    TIMEOUT: 30000
  }
}

// Admin Configuration
export const ADMIN_CONFIG = {
  DEFAULT_LOGS_LIMIT: 100,
  DEFAULT_FEEDBACK_DAYS: 30,
  POLLING_INTERVALS: {
    TASKS: 5000,      // 5 seconds
    HEALTH: 30000,    // 30 seconds
    STATS: 60000      // 1 minute
  },
  ACTIONS: {
    CLEAR_CACHE: 'clearCache',
    CLEANUP_SESSIONS: 'cleanupSessions', 
    CLEAR_FEEDBACK: 'clearFeedback',
    CLEAR_LOGS: 'clearLogs'
  }
}

// External Services Configuration
export const EXTERNAL_SERVICES = {
  TRANSLATE_API: {
    // Use relative path through Nginx Gateway (routes to processor service)
    BASE_URL: import.meta.env.VITE_TRANSLATE_API_URL || '/processor',
    TIMEOUT: 10000
  },
  STP_SERVICE: {
    // Use relative path through Nginx Gateway (routes to processor service)
    BASE_URL: import.meta.env.VITE_STP_SERVICE_URL || '/processor',
    TIMEOUT: 10000
  },
  PROCESSOR: {
    // Use relative path through Nginx Gateway
    BASE_URL: import.meta.env.VITE_PROCESSOR_URL || '',
    TIMEOUT: 10000,
    ENDPOINTS: {
      SERVICES_HEALTH: '/services/health',
      WEBHOOK_STATUS: '/webhook/status',
      WEBHOOK_ENABLE: '/webhook/enable',
      WEBHOOK_DISABLE: '/webhook/disable',
      WEBHOOK_TOGGLE: '/webhook/toggle'
    }
  }
}