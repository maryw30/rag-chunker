_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st",
    "vs", "etc", "eg", "ie", "fig", "vol", "approx",
    "dept", "inc", "ltd", "co", "corp", "gov", "no",
}


def split_sentences(text):
    text = text.strip()
    if not text:
        return []

    sentences = []
    start = 0
    i = 0
    length = len(text)

    while i < length:
        char = text[i]
        if char not in ".!?":
            i += 1
            continue

        j = i + 1
        while j < length and text[j] in ".!?":
            j += 1

        if j < length and text[j].isspace() and not _is_abbreviation(text, i):
            k = j
            while k < length and text[k].isspace():
                k += 1
            sentences.append(text[start:j].strip())
            start = k
            i = k
            continue

        i = j

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _is_abbreviation(text, dot_index):
    j = dot_index
    while j > 0 and text[j - 1].isalpha():
        j -= 1
    word = text[j:dot_index]
    if not word:
        return False
    if len(word) == 1:
        return True
    return word.lower() in _ABBREVIATIONS
