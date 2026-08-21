from rag_chunker.tokens import estimate_tokens


def test_empty_and_whitespace_only_is_zero():
    assert estimate_tokens("") == 0
    assert estimate_tokens("   \n  ") == 0


def test_word_characters_cost_a_quarter_token_each():
    assert estimate_tokens("test estimate") == 3


def test_digits_cost_one_token_per_run_regardless_of_length():
    assert estimate_tokens("123") == 1
    assert estimate_tokens("123 456") == 2


def test_cjk_characters_cost_one_token_each():
    assert estimate_tokens("日本語") == 3


def test_tiny_content_floors_to_one_token():
    assert estimate_tokens(".") == 1
    assert estimate_tokens("a") == 1


def test_newlines_add_to_the_estimate():
    base = estimate_tokens("word")
    with_newlines = estimate_tokens("word\n\n\n\n")
    assert with_newlines > base


def test_longer_prose_grows_with_length():
    short = estimate_tokens("one short sentence here")
    long = estimate_tokens("one short sentence here " * 10)
    assert long > short * 5
