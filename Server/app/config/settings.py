"""
DEPRECATED: This module is kept for backward compatibility only.

Please use the following import instead:
    from app.config import get_settings, Settings, settings

This file re-exports from app.config.__init__ to maintain backward compatibility
with existing code that imports from app.config.settings.
"""

# Re-export everything from __init__ for backward compatibility
from app.config import (
    Settings,
    get_settings,
    settings,
    BaseConfig,
    SecurityConfig,
    LLMConfig,
    RAGConfig,
    IntegrationsConfig,
    FeaturesConfig,
)

# Maintain the same exports
__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "BaseConfig",
    "SecurityConfig",
    "LLMConfig",
    "RAGConfig",
    "IntegrationsConfig",
    "FeaturesConfig",
]
