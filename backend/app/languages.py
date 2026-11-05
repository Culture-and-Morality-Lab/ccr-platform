"""ISO 639-1 code to English language name, for DISPLAY only.

Codes stay the stored and exported form everywhere - run metadata, the results
CSV, construct YAML, and the structured fields on warnings - because they are
part of the reproducibility record and the output contract. This module only
decides what a human is shown (PI request 2026-09-04: "change the name of
languages from acronyms to actual names").

Coverage is checked by a test against both sources that can produce a code: the
selectable list in main.py and every language set in the model registry (a
detected language can be any of them). Unknown codes fall back to the code
itself, so a new detector output degrades to today's behavior rather than
rendering "None".
"""

from __future__ import annotations

NAMES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "as": "Assamese",
    "az": "Azerbaijani", "be": "Belarusian", "bg": "Bulgarian", "bn": "Bengali",
    "br": "Breton", "bs": "Bosnian", "ca": "Catalan", "cs": "Czech",
    "cy": "Welsh", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "eo": "Esperanto", "es": "Spanish", "et": "Estonian",
    "eu": "Basque", "fa": "Persian", "fi": "Finnish", "fr": "French",
    "fy": "Western Frisian", "ga": "Irish", "gd": "Scottish Gaelic",
    "gl": "Galician", "gu": "Gujarati", "ha": "Hausa", "he": "Hebrew",
    "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian", "hy": "Armenian",
    "id": "Indonesian", "is": "Icelandic", "it": "Italian", "ja": "Japanese",
    "jv": "Javanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "ku": "Kurdish", "ky": "Kyrgyz",
    "la": "Latin", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mg": "Malagasy", "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian",
    "mr": "Marathi", "ms": "Malay", "my": "Burmese", "ne": "Nepali",
    "nl": "Dutch", "no": "Norwegian", "om": "Oromo", "or": "Odia",
    "pa": "Punjabi", "pl": "Polish", "ps": "Pashto", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sa": "Sanskrit", "sd": "Sindhi",
    "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali",
    "sq": "Albanian", "sr": "Serbian", "su": "Sundanese", "sv": "Swedish",
    "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "th": "Thai",
    "tl": "Tagalog", "tr": "Turkish", "ug": "Uyghur", "uk": "Ukrainian",
    "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese", "xh": "Xhosa",
    "yi": "Yiddish", "zh": "Chinese",
    # langdetect reports these two rather than a bare "zh".
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
}


# Writing system(s) each language is normally written in, for the item-language
# check (spec 0011). Only languages NOT written in Latin script are listed;
# every other code is Latin. Script ids are the first word of the Unicode
# character name, lowercased ("ARABIC LETTER ALEF" -> "arabic"), which is how
# warnings_engine reads the script of an item.
SCRIPTS: dict[str, frozenset[str]] = {
    code: frozenset(s.split()) for code, s in {
        "am": "ethiopic", "ar": "arabic", "as": "bengali", "be": "cyrillic",
        "bg": "cyrillic", "bn": "bengali", "el": "greek", "fa": "arabic",
        "gu": "gujarati", "he": "hebrew", "hi": "devanagari", "hy": "armenian",
        "ja": "cjk hiragana katakana", "ka": "georgian", "kk": "cyrillic",
        "km": "khmer", "kn": "kannada", "ko": "hangul cjk", "ku": "latin arabic",
        "ky": "cyrillic", "lo": "lao", "mk": "cyrillic", "ml": "malayalam",
        "mn": "cyrillic mongolian", "mr": "devanagari", "my": "myanmar",
        "ne": "devanagari", "or": "oriya", "pa": "gurmukhi", "ps": "arabic",
        "ru": "cyrillic", "sa": "devanagari", "sd": "arabic", "si": "sinhala",
        "sr": "cyrillic latin", "ta": "tamil", "te": "telugu", "th": "thai",
        "ug": "arabic", "uk": "cyrillic", "ur": "arabic", "uz": "latin cyrillic",
        "yi": "hebrew", "zh": "cjk",
    }.items()
}
KNOWN_SCRIPTS: frozenset[str] = frozenset({"latin"}).union(*SCRIPTS.values())
_SCRIPT_LABELS = {"cjk": "Chinese (Han)"}


def scripts(code: str) -> frozenset[str]:
    """Writing systems a language is written in; Latin unless listed above."""
    key = str(code).strip().lower()
    return SCRIPTS.get(key) or SCRIPTS.get(key.split("-")[0]) or frozenset({"latin"})


def display_script(script: str) -> str:
    return _SCRIPT_LABELS.get(script, script.title())


def display(code: str | None) -> str:
    """Human-readable language name; falls back to the code when unknown."""
    if not code:
        return ""
    key = str(code).strip().lower()
    return NAMES.get(key) or NAMES.get(key.split("-")[0], str(code))


def labelled(code: str | None) -> str:
    """Name with the code kept alongside, for places where the code is still
    load-bearing (a run's metadata records the code, so a researcher comparing
    the two should not have to translate)."""
    name = display(code)
    return f"{name} ({code})" if code and name != code else name


# Named language sets from the model registry, rendered for humans. The set
# NAME stays the machine-checkable identity in models.yaml (design doc 12
# bans a bare "multilingual" label); this is only its display form.
SET_NAMES: dict[str, str] = {
    "xlm_roberta_100": "100+ languages (XLM-RoBERTa coverage)",
}


def display_set(set_name: str) -> str:
    return SET_NAMES.get(set_name, set_name)
