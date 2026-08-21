from rag_chunker.sentences import split_sentences


def test_empty_and_whitespace_only():
    assert split_sentences("") == []
    assert split_sentences("   \n  ") == []


def test_basic_split_on_terminal_punctuation():
    result = split_sentences("Hello world. This is a test.")
    assert result == ["Hello world.", "This is a test."]


def test_no_trailing_punctuation_becomes_final_sentence():
    result = split_sentences("Hello world. No ending here")
    assert result == ["Hello world.", "No ending here"]


def test_known_abbreviation_does_not_split():
    result = split_sentences("Dr. Chen arrived on time.")
    assert result == ["Dr. Chen arrived on time."]


def test_single_letter_initial_does_not_split():
    result = split_sentences("See the docs, e.g. the README, for details.")
    assert result == ["See the docs, e.g. the README, for details."]


def test_period_with_no_following_space_does_not_split():
    result = split_sentences("Download v1.4 now. It fixes bugs.")
    assert result == ["Download v1.4 now.", "It fixes bugs."]


def test_punctuation_run_is_kept_together():
    result = split_sentences("Really?! Are you sure?")
    assert result == ["Really?!", "Are you sure?"]


def test_two_short_sentences_split_normally():
    result = split_sentences("Yes. No.")
    assert result == ["Yes.", "No."]
