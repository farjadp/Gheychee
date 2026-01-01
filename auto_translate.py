#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATH: auto_translate.py
TIMESTAMP: 2026-01-01 13:30 EST
VERSION: v2.0.0
DESIGN: Script for automated translation of message files using external API.
CONCEPT: "Automated Localization."

Automated translation of untranslated strings in localization files.
Uses line-by-line analysis to replace only string values,
preserving file structure, variable names, and Python syntax.
"""

import sys
import re
import importlib.util
from pathlib import Path
from typing import Dict, Tuple, Optional
from deep_translator import GoogleTranslator

# Path to localization files directory
LANGUAGES_DIR = Path(__file__).parent / "CONFIG" / "LANGUAGES"
EN_FILE = LANGUAGES_DIR / "messages_EN.py"

# Language code mapping for Google Translate
LANGUAGE_CODES = {
    'KK': 'kk',  # Kazakh
    'FA': 'fa',  # Persian
    'IT': 'it',  # Italian
    'JA': 'ja',  # Japanese
    'TL': 'tl',  # Tagalog
    'UK': 'uk',  # Ukrainian
    'TR': 'tr',  # Turkish
    'TH': 'th',  # Thai
    'HA': 'ha',  # Hausa
    'ID': 'id',  # Indonesian
    'UR': 'ur',  # Urdu
    'KO': 'ko',  # Korean
    'AR': 'ar',  # Arabic
    'IN': 'hi',  # Hindi
    'RU': 'ru',  # Russian
}

# Exceptions - strings not to be translated
SKIP_PATTERNS = [
    # Removed "only emoji" pattern - now strings with emojis will be translated
    r'^[\d\s%\.]+$',  # Only numbers, spaces, dots
    r'^[A-Z_]+$',  # Only uppercase letters and underscores (no text)
    r'^users/\{user_id\}/cookie\.txt$',
    r'^formats_\{user_id\}\.txt$',
    r'^\[.*\]$',  # Log messages
    r'^generic:.*$',
    r'^youtube$',
    r'^tiktok$',
    r'^instagram$',
    r'^twitter$',
    r'^custom$',
    r'^MESSAGE_ID_INVALID$',
    r'^MESSAGE_DELETE_FORBIDDEN$',
    r'^True$',
    r'^False$',
]

# Variables not to be translated (by suffix)
SKIP_SUFFIXES = [
    '_EMOJI',
    # Removed '_BUTTON_MSG' - now buttons will be translated
    '_INACTIVE_MSG',
    '_UNAVAILABLE_MSG',
    '_VALUES',
    '_FILE_NAME_MSG',
]


def load_messages_class(file_path: Path) -> Optional[type]:
    """Loads Messages class from file."""
    try:
        spec = importlib.util.spec_from_file_location("messages_module", file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules['messages_module'] = module
        spec.loader.exec_module(module)
        if not hasattr(module, 'Messages'):
            return None
        return module.Messages
    except Exception:
        return None


def get_class_attributes(cls: type) -> Dict[str, any]:
    """Extracts all class attributes."""
    attributes = {}
    for attr_name in dir(cls):
        if attr_name.startswith('_'):
            continue
        attr_value = getattr(cls, attr_name)
        if callable(attr_value):
            continue
        attributes[attr_name] = attr_value
    return attributes


def should_skip_translation(var_name: str, value: str) -> bool:
    """Checks if translation of this variable should be skipped."""
    value_str = str(value)
    
    # Check suffixes
    if any(var_name.endswith(suffix) for suffix in SKIP_SUFFIXES):
        return True
    
    # Check patterns
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, value_str):
            return True
    
    # Skip very short strings (less than 2 chars), but only if not emoji with text
    # Remove emojis, HTML tags and variables to check text length
    text_without_emoji = re.sub(r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U00002700-\U000027BF]+', '', value_str)
    text_without_html = re.sub(r'<[^>]+>', '', text_without_emoji)  # Remove HTML tags
    text_without_vars = re.sub(r'\{[^}]+\}', '', text_without_html)  # Remove variables
    if len(text_without_vars.strip()) < 2 and len(value_str.strip()) < 8:
        # If less than 2 chars remaining after removing emojis, HTML and variables - skip
        return True
    
    # Skip only multi-line strings with triple quotes
    # Strings with escaped \n (single-line) will be translated
    if value_str.startswith('"""') or value_str.startswith("'''"):
        return True
    
    return False


def protect_variables(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Protects variables in curly braces from translation.
    Returns (protected text, replacements dictionary)
    Uses unique marker that cannot appear in text.
    """
    replacements = {}
    protected_text = text
    counter = 0
    
    # Find all {variable_name} and replace them with placeholders
    # Use unique marker with zero width space to avoid conflicts
    pattern = r'\{([^}]+)\}'
    matches = list(re.finditer(pattern, protected_text))
    
    # Process in reverse order to avoid messing up indices
    for match in reversed(matches):
        # Use unique marker with zero width space
        placeholder = f"\u200B__VAR_{counter}__\u200B"
        replacements[placeholder] = match.group(0)  # Save {variable_name}
        protected_text = protected_text[:match.start()] + placeholder + protected_text[match.end():]
        counter += 1
    
    return protected_text, replacements


def restore_variables(text: str, replacements: Dict[str, str]) -> str:
    """Restores variables from placeholders."""
    if text is None:
        return ""
    restored = text
    for placeholder, original in replacements.items():
        restored = restored.replace(placeholder, original)
    return restored


def parse_string_value(line: str) -> Optional[Tuple[str, str, str, bool]]:
    """
    Parses assignment line and extracts variable name, value and format.
    Returns (var_name, value, quote_type, is_fstring) or None.
    Works only with single-line strings.
    """
    # Skip strings that are clearly multi-line (with triple quotes)
    if '"""' in line or "'''" in line:
        return None
    
    # Skip lines ending with = (start of multi-line assignment)
    if line.rstrip().endswith('=') or line.rstrip().endswith('=('):
        return None
    
    # Check if it is f-string
    is_fstring = line.strip().startswith('f') or line.strip().startswith('F')
    
    # Pattern: VAR_NAME = "value" or VAR_NAME = 'value' or f"value" (single-line string)
    # Consider that value may contain \n as chars, but not real line breaks
    pattern = r'^(\s*)(?:f|F)?([A-Z][A-Z0-9_]*)\s*=\s*(?:f|F)?(["\'])(.*?)(["\'])$'
    match = re.match(pattern, line.rstrip(), re.DOTALL)
    if match:
        var_name = match.group(2)
        quote_char = match.group(3)
        value = match.group(4)
        
        # Check that it is indeed a single-line string
        # If source line has real line breaks (not \n), skip
        if '\n' in line and not line.rstrip().endswith(quote_char):
            return None
        
        # Обрабатываем экранированные кавычки
        value = value.replace(f'\\{quote_char}', quote_char)
        # Обрабатываем экранированные переносы строк
        value = value.replace('\\n', '\n')
        value = value.replace('\\t', '\t')
        
        return (var_name, value, quote_char, is_fstring)
    
    return None


def translate_string(text: str, target_lang: str, max_retries: int = 3) -> str:
    """Translates string to target language protecting variables in curly braces."""
    # Protect variables
    protected_text, replacements = protect_variables(text)
    
    # Translate protected text
    for attempt in range(max_retries):
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            translated = translator.translate(protected_text)
            
            # If translation returned None (e.g. for emoji-only strings), return original text
            if translated is None:
                # Restore variables from original text
                result = restore_variables(text, replacements)
                if result is None:
                    result = text
                result = result.replace('\u200B', '')
                return result
            
            # Restore variables
            translated = restore_variables(translated, replacements)
            
            # Check that result is not None
            if translated is None:
                translated = text
            
            # Remove invisible characters (zero-width-space) that might have appeared
            translated = translated.replace('\u200B', '')
            
            return translated
        except Exception as e:
            if attempt and attempt < max_retries - 1:
                import time
                time.sleep(1)  # Pause before retry
                continue
            print(f"        ⚠️  Translation error: {e}")
            # Restore variables even on error
            result = restore_variables(text, replacements)
            if result is None:
                result = text
            result = result.replace('\u200B', '')
            return result
    
    # If all attempts failed, return original text
    result = restore_variables(text, replacements)
    if result is None:
        result = text
    result = result.replace('\u200B', '')
    return result


def auto_translate_file(lang_file: Path, lang_code: str, dry_run: bool = False, batch_size: int = 20, start_line: Optional[int] = None, end_line: Optional[int] = None) -> int:
    """Automatically translates untranslated strings in file."""
    print(f"\n🌐 Processing: {lang_file.name} ({lang_code})")
    
    # Load reference file
    en_messages = load_messages_class(EN_FILE)
    if en_messages is None:
        print("    ❌ Failed to load reference file")
        return 0
    
    en_attributes = get_class_attributes(en_messages)
    
    # Load target file
    lang_messages = load_messages_class(lang_file)
    if lang_messages is None:
        print("    ❌ Failed to load file")
        return 0
    
    lang_attributes = get_class_attributes(lang_messages)
    
    # Find untranslated strings
    untranslated = {}
    for var_name, en_value in en_attributes.items():
        if var_name in lang_attributes:
            lang_value = lang_attributes[var_name]
            if lang_value == en_value and not should_skip_translation(var_name, str(en_value)):
                untranslated[var_name] = str(en_value)
    
    if not untranslated:
        print("    ✅ All strings translated!")
        return 0
    
    print(f"    📊 Untranslated strings found: {len(untranslated)}")
    
    # Get target language code
    target_lang_code = LANGUAGE_CODES.get(lang_code, lang_code.lower())
    
    # Read file content line by line
    with open(lang_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Determine line range for processing (0-based indices)
    if start_line is not None:
        start_idx = max(0, start_line - 1)  # Convert to 0-based index
        print(f"    📍 Range start: line {start_line}")
    else:
        start_idx = 0
    
    if end_line is not None:
        end_idx = min(len(lines), end_line)  # end_line is 1-based but exclusive
        print(f"    📍 Range end: line {end_line}")
    else:
        end_idx = len(lines)
    
    if start_line is not None or end_line is not None:
        print(f"    📊 Processing lines {start_idx + 1}-{end_idx} of {len(lines)}")
    
    translated_count = 0
    i = start_idx
    
    # Process file line by line in specified range
    while i < end_idx and i < len(lines):
        line = lines[i]
        
        # Parse line (single-line only)
        parsed = parse_string_value(line)
        if parsed:
            var_name, value, quote_char, is_fstring = parsed
            
            # Check if variable needs translation
            if var_name in untranslated:
                # Skip lines with real line breaks (multi-line)
                if '\n' in value and value.count('\n') > 0:
                    # Check if real line breaks or escaped \n
                    # If source line has real line breaks, skip
                    if line.count('\n') > 1 or (line.rstrip().endswith(quote_char) and '\n' in line):
                        i += 1
                        continue
                
                # Check f-string without variables - skip such lines
                if is_fstring:
                    # Check if there are variables in string
                    if not re.search(r'\{[^}]+\}', value):
                        # f-string without variables - skip
                        i += 1
                        continue
                
                print(f"    🔄 Translating {var_name} (line {i+1})...", end=' ')
                
                # Translate
                translated_value = translate_string(value, target_lang_code)
                
                # Check that translation didn't return None
                if translated_value is None:
                    translated_value = value
                    print("⚠️  (translation returned None, original value kept)")
                
                if translated_value != value:
                    # Escape special chars for Python string
                    # Restore \n and \t back to escaped forms
                    escaped_value = translated_value.replace('\\', '\\\\')  # First escape backslashes
                    escaped_value = escaped_value.replace('\n', '\\n')  # Then line breaks
                    escaped_value = escaped_value.replace('\t', '\\t')  # Then tabs
                    escaped_value = escaped_value.replace(quote_char, f'\\{quote_char}')  # Then quotes
                    
                    # Replace value in string
                    # Consider f-string prefix
                    f_prefix = 'f' if is_fstring else ''
                    # Use more precise regex
                    pattern = r'=\s*(?:f|F)?' + re.escape(quote_char) + r'.*?' + re.escape(quote_char)
                    new_line = re.sub(
                        pattern,
                        f'= {f_prefix}{quote_char}{escaped_value}{quote_char}',
                        line,
                        count=1
                    )
                    
                    # If it was f-string but no variables after translation, remove f
                    if is_fstring and not re.search(r'\{[^}]+\}', escaped_value):
                        new_line = new_line.replace('= f', '= ', 1).replace('= F', '= ', 1)
                    
                    if not dry_run:
                        lines[i] = new_line
                    
                    translated_count += 1
                    print("✅")
                else:
                    print("⏭️  (no changes)")
        
        i += 1
        
        # Limit translation count per run
        if translated_count >= batch_size:
            print(f"    ⏸️  Limit reached ({batch_size} translations per batch)")
            break
    
    # Save file
    if not dry_run and translated_count > 0:
        with open(lang_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"    💾 Saved {translated_count} translations")
    
    return translated_count


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated translation of untranslated strings')
    parser.add_argument('--lang', help='Language code for translation (e.g. KK, FA)')
    parser.add_argument('--dry-run', action='store_true', help='Only show what will be translated')
    parser.add_argument('--batch', type=int, default=20, help='Translations per batch (default 20)')
    parser.add_argument('--start-line', type=int, help='Start line for processing (1-based, inclusive)')
    parser.add_argument('--end-line', type=int, help='End line for processing (1-based, inclusive)')
    
    args = parser.parse_args()
    
    if args.lang:
        lang_code = args.lang.upper()
        lang_file = LANGUAGES_DIR / f"messages_{lang_code}.py"
        if not lang_file.exists():
            print(f"❌ File {lang_file} not found")
            return 1
        
        # Validate line range
        if args.start_line is not None and args.start_line < 1:
            print(f"❌ Start line must be >= 1")
            return 1
        
        if args.end_line is not None and args.end_line < 1:
            print(f"❌ End line must be >= 1")
            return 1
        
        if args.start_line is not None and args.end_line is not None:
            if args.start_line > args.end_line:
                print(f"❌ Start line ({args.start_line}) cannot be greater than end line ({args.end_line})")
                return 1
        
        count = auto_translate_file(lang_file, lang_code, args.dry_run, args.batch, args.start_line, args.end_line)
        print(f"\n✅ Translated lines: {count}")
        if count and count > 0:
            print(f"💡 Run again to translate next {args.batch} lines")
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
