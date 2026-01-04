"""
ProductionTextCleaner - Advanced text cleaning using ftfy + wordninja
Fixes unicode corruption and splits concatenated words intelligently
"""

import re
import unicodedata
from typing import Set

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False
    print("⚠️ ftfy not available. Install with: pip install ftfy")

try:
    import wordninja
    WORDNINJA_AVAILABLE = True
except ImportError:
    WORDNINJA_AVAILABLE = False
    print("⚠️ wordninja not available. Install with: pip install wordninja")


class ProductionTextCleaner:
    """
    Advanced text cleaner using ftfy + wordninja
    Fixes unicode corruption and intelligently splits concatenated words
    """
    
    def __init__(self, min_word_length: int = 4, verbose: bool = False):
        """
        Initialize text cleaner
        
        Args:
            min_word_length: Minimum word length for splitting
            verbose: Enable detailed logging
        """
        self.min_word_length = min_word_length
        self.verbose = verbose
        
        # Unicode fixes for common corruptions
        self.unicode_fixes = {
            'ï¬پ': 'fi', 'ï¬‚': 'fl', 'ï¬€': 'ff', 'ï¬ƒ': 'ffi', 'ï¬„': 'ffl',
            'â€™': "'", 'â€œ': '"', 'â€': '"', 'â€"': '-', 'Â': ' '
        }
        
        # Spacing patterns
        self._init_spacing_patterns()
        
        # Protected terms (don't split these)
        self.protected_terms = {
            'eudr', 'cbam', 'gdp', 'eu', 'us', 'uk', 'un', 'ai', 'ml', 'api',
            'covid', 'covid-19', 'thereby', 'therefore', 'however', 'moreover',
            'furthermore', 'nevertheless', 'sustainable', 'development', 'stakeholder',
            'biodiversity', 'deforestation', 'agricultural', 'environmental'
        }
        
        if self.verbose:
            print(f"✓ ProductionTextCleaner initialized")
            print(f"  Min word length: {min_word_length}")
            print(f"  ftfy: {'available' if FTFY_AVAILABLE else 'NOT available'}")
            print(f"  wordninja: {'available' if WORDNINJA_AVAILABLE else 'NOT available'}")
    
    def _init_spacing_patterns(self):
        """Initialize spacing patterns"""
        self.spacing_patterns = [
            # High-confidence punctuation fixes
            (r'([.!?])([A-Z])', r'\1 \2'),
            (r'([,;:])([A-Za-z])', r'\1 \2'),
            (r'(\d)([A-Za-z])', r'\1 \2'),
            (r'([a-z])\(', r'\1 ('),
            (r'\)([A-Z])', r') \1'),
            
            # Specific problematic patterns
            (r'\)with([a-z])', r') with \1'),
            (r'([a-z])entering([a-z])', r'\1 entering \2'),
            (r'([a-z])goods([a-z])', r'\1 goods \2'),
            
            # Academic/policy terms
            (r'([a-z])(EUDR|CBAM|GDP|COVID-19)([a-z])', r'\1 \2 \3'),
            
            # Common words
            (r'([a-z])(and|or|but|the|of|in|on|at|to|for|with|by|from)([A-Z])', r'\1 \2 \3'),
            
            # General camelCase
            (r'([a-z]{3,})([A-Z][a-z]{3,})', r'\1 \2'),
        ]
    
    def clean_text(self, text: str) -> str:
        """
        Clean text using ftfy + wordninja pipeline
        
        Args:
            text: Raw text from PDF extraction
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        original_length = len(text)
        
        if self.verbose:
            print(f"\n🔄 Processing ({original_length} chars): {text[:50]}...")
        
        # Step 1: Fix unicode corruption with ftfy
        if FTFY_AVAILABLE:
            text = ftfy.fix_text(text)
        
        # Apply manual unicode fixes
        for corrupted, fixed in self.unicode_fixes.items():
            text = text.replace(corrupted, fixed)
        
        text = unicodedata.normalize('NFKC', text)
        
        # Step 2: Apply spacing patterns
        spacing_fixes = 0
        for pattern, replacement in self.spacing_patterns:
            before = text
            text = re.sub(pattern, replacement, text)
            if text != before:
                spacing_fixes += 1
        
        if self.verbose and spacing_fixes > 0:
            print(f"    📐 Applied {spacing_fixes} spacing fixes")
        
        # Step 3: Smart word splitting with wordninja
        if WORDNINJA_AVAILABLE:
            words = text.split()
            result = []
            splits_applied = 0
            
            for word in words:
                # Extract alphabetic core
                match = re.search(r'([a-zA-Z]+)', word)
                if not match:
                    result.append(word)
                    continue
                
                alphabetic_part = match.group(1)
                prefix = word[:match.start()]
                suffix = word[match.end():]
                
                # Decide whether to split
                should_split = (
                    len(alphabetic_part) >= self.min_word_length and
                    alphabetic_part.lower() not in self.protected_terms and
                    (len(alphabetic_part) >= 12 or re.search(r'[a-z][A-Z]', alphabetic_part))
                )
                
                if should_split:
                    try:
                        split_words = wordninja.split(alphabetic_part)
                        
                        # Basic validation: check if split makes sense
                        if len(split_words) > 1 and all(len(w) > 1 for w in split_words):
                            # Apply the split
                            if prefix:
                                split_words[0] = prefix + split_words[0]
                            if suffix:
                                split_words[-1] = split_words[-1] + suffix
                            
                            result.extend(split_words)
                            splits_applied += 1
                            
                            if self.verbose:
                                print(f"    ✅ Split: '{alphabetic_part}' → {split_words}")
                        else:
                            result.append(word)
                    except Exception as e:
                        if self.verbose:
                            print(f"    ⚠️ wordninja failed on '{alphabetic_part}': {e}")
                        result.append(word)
                else:
                    result.append(word)
            
            text = ' '.join(result)
            
            if self.verbose and splits_applied > 0:
                print(f"    🔪 Applied {splits_applied} word splits")
        
        # Step 4: Final cleanup
        text = re.sub(r'\s+', ' ', text).strip()
        
        if self.verbose:
            print(f"  📝 Cleaning complete: {original_length} → {len(text)} chars")
        
        return text


print("✅ ProductionTextCleaner ready!")