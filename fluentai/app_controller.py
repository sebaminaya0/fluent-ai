"""Non-UI translation logic for the desktop app.

``TranslationController`` owns the model-backed translation and the pure
text/language helpers that used to live on the ``FluentAIGUI`` God class. It has
no Tkinter dependency, so it can be unit-tested directly. The GUI delegates to it
and keeps only view/orchestration concerns.
"""

import logging
import re

logger = logging.getLogger(__name__)

VALID_LANGUAGES = ("es", "en", "de", "fr")

# Latin character set used to sanity-check transcribed text (covers ES/DE/FR).
_LATIN_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "áéíóúüñÁÉÍÓÚÜÑ¿¡äöüÄÖÜßàâäçèêëïîôùûüÿÀÂÄÇÈÊËÏÎÔÙÛÜŸ"
    ".,;:!?()[]{}\"'-_ "
)

# Indicator words/characters for cheap language detection used for TTS voice.
_LANG_INDICATORS = {
    "es": {
        "words": [
            "el",
            "la",
            "de",
            "que",
            "y",
            "es",
            "en",
            "un",
            "una",
            "con",
            "por",
            "para",
            "hola",
            "gracias",
            "sí",
            "no",
            "dónde",
            "cuándo",
            "cómo",
            "qué",
        ],
        "chars": ["ñ", "á", "é", "í", "ó", "ú", "¿", "¡"],
    },
    "de": {
        "words": [
            "der",
            "die",
            "das",
            "und",
            "ich",
            "sie",
            "mit",
            "für",
            "auf",
            "von",
            "ist",
            "war",
            "haben",
            "werden",
            "sein",
            "nicht",
            "auch",
            "aber",
            "oder",
            "wie",
        ],
        "chars": ["ä", "ö", "ü", "ß"],
    },
    "fr": {
        "words": [
            "le",
            "la",
            "les",
            "et",
            "de",
            "je",
            "tu",
            "il",
            "elle",
            "nous",
            "vous",
            "ils",
            "elles",
            "avec",
            "pour",
            "sur",
            "dans",
            "mais",
            "ou",
            "où",
            "comment",
        ],
        "chars": ["à", "â", "ä", "ç", "è", "ê", "ë", "ï", "î", "ô", "ù", "û", "ü", "ÿ"],
    },
}


class TranslationController:
    """Owns model-backed translation and pure text/language helpers."""

    def __init__(self, model_loader):
        self.model_loader = model_loader

    def translate(self, text, src_lang, dst_lang):
        """Translate text via the appropriate model. Returns text or None.

        Multi-sentence input is split and translated sentence-by-sentence so the
        model's max_length doesn't silently truncate longer utterances.
        """
        try:
            translator = self.model_loader.get_model(src_lang, dst_lang)
            if not translator:
                logger.error("No translator for %s -> %s", src_lang, dst_lang)
                return None
            outputs = []
            for sentence in self._split_sentences(text):
                try:
                    result = translator(sentence, max_length=512, do_sample=False)
                except Exception as pipeline_error:
                    logger.warning(
                        "Translator call failed, retrying: %s", pipeline_error
                    )
                    result = translator(sentence)
                outputs.append(result[0]["translation_text"].strip())
            return " ".join(o for o in outputs if o).strip()
        except Exception as e:
            logger.error("Translation error: %s", e)
            return None

    @staticmethod
    def _split_sentences(text):
        """Split text on ./!/? boundaries (keeping punctuation).

        Returns ``[text]`` when there are no sentence boundaries.
        """
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p for p in parts if p] or [text]

    def determine_target_language(self, src_lang, target_selection):
        """Resolve the destination language from a selection (or 'auto')."""
        if target_selection == "auto":
            if src_lang == "es":
                return "en"
            if src_lang in ("en", "de", "fr"):
                return "es"
            return "en"

        valid_combinations = {
            "es": ["en", "de", "fr"],
            "en": ["es", "de", "fr"],
            "de": ["es", "en"],
            "fr": ["es", "en"],
        }
        if target_selection in valid_combinations.get(src_lang, []):
            return target_selection
        return None

    def validate_text(self, text, detected_language):
        """Validate transcribed text is plausible for the supported languages."""
        cleaned = text.strip()
        if len(cleaned) < 2:
            return False

        non_latin = set(text) - _LATIN_CHARS
        if non_latin and len(non_latin) / len(set(text)) > 0.2:
            return False

        return detected_language in VALID_LANGUAGES

    def detect_tts_language(self, text):
        """Cheaply guess the language of text to pick a TTS voice."""
        lowered = text.lower()
        scores = {
            lang: sum(1 for w in ind["words"] if w in lowered)
            + sum(1 for c in ind["chars"] if c in lowered)
            for lang, ind in _LANG_INDICATORS.items()
        }
        max_score = max(scores.values())
        if max_score == 0:
            return "en"
        for lang, score in scores.items():
            if score == max_score:
                return lang
        return "en"
