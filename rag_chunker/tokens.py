import re

_CJK_RANGES = (
    "぀-ヿ"  # hiragana, katakana
    "㐀-䶿"  # CJK extension A
    "一-鿿"  # CJK unified ideographs
    "豈-﫿"  # CJK compatibility ideographs
    "가-힣"  # hangul syllables
)
_CJK_RE = re.compile("[" + _CJK_RANGES + "]")
_WORD_RE = re.compile("[^\\W\\d_" + _CJK_RANGES + "]+", re.UNICODE)
_DIGIT_RUN_RE = re.compile(r"\d+")
_SYMBOL_RE = re.compile(r"[^\w\s]", re.UNICODE)


def estimate_tokens(text):
    if not text or not text.strip():
        return 0

    cjk_tokens = len(_CJK_RE.findall(text))
    word_chars = sum(len(word) for word in _WORD_RE.findall(text))
    digit_tokens = len(_DIGIT_RUN_RE.findall(text))
    symbol_tokens = len(_SYMBOL_RE.findall(text)) * 0.5
    newline_tokens = text.count("\n") * 0.5

    total = cjk_tokens + word_chars / 4.0 + digit_tokens + symbol_tokens + newline_tokens
    return max(1, round(total))
