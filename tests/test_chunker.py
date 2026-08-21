import json

import pytest

from rag_chunker.chunker import chunk_markdown, chunks_to_jsonl


def test_single_section_produces_one_chunk_with_heading_prefix():
    doc = "# Title\n\nHello world. This is a test.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=64)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.heading_path == ["Title"]
    assert chunk.text == "Title\n\nHello world.\n\nThis is a test."
    assert chunk.body == "Hello world.\n\nThis is a test."
    assert chunk.start_line == 3
    assert chunk.end_line == 3
    assert chunk.index == 0


def test_heading_prefix_can_be_disabled():
    doc = "# Title\n\nHello world.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=0, heading_prefix=False)
    assert len(chunks) == 1
    assert chunks[0].text == chunks[0].body == "Hello world."


def test_nested_headings_produce_heading_path_and_reset_on_siblings():
    doc = "# A\n\n## B\n\nText under B.\n\n# C\n\nText under C.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=0)
    assert [c.heading_path for c in chunks] == [["A", "B"], ["C"]]
    assert chunks[0].body == "Text under B."
    assert chunks[1].body == "Text under C."


def test_heading_with_no_body_produces_no_chunk():
    doc = "# A\n\n## B\n\nOnly B has text.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=0)
    assert len(chunks) == 1
    assert chunks[0].heading_path == ["A", "B"]


def test_code_block_flagged_oversized_when_it_exceeds_the_budget():
    doc = "# T\n\n```\n" + "x" * 200 + "\n```\n"
    chunks = chunk_markdown(doc, max_tokens=5, overlap=0)
    assert len(chunks) == 1
    assert chunks[0].oversized is True


def test_small_paragraph_is_not_flagged_oversized():
    doc = "# T\n\nShort.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=0)
    assert chunks[0].oversized is False


def test_overlap_zero_means_no_carry_between_chunks():
    doc = "Short one. This is a longer trailing sentence with quite a few extra words in it today."
    chunks = chunk_markdown(doc, max_tokens=6, overlap=0, heading_prefix=False)
    assert len(chunks) >= 2
    second_sentence = (
        "This is a longer trailing sentence with quite a few extra words in it today."
    )
    assert chunks[1].body == second_sentence


def test_overlap_carries_tail_of_previous_chunk_into_the_next():
    doc = "Short one. This is a longer trailing sentence with quite a few extra words in it today."
    chunks = chunk_markdown(doc, max_tokens=6, overlap=2, heading_prefix=False)
    assert len(chunks) >= 2
    second_sentence = (
        "This is a longer trailing sentence with quite a few extra words in it today."
    )
    assert chunks[1].body != second_sentence
    assert chunks[1].body.endswith(second_sentence)
    assert "one." in chunks[1].body


def test_overlap_resets_at_a_new_heading():
    doc = (
        "# A\n\n"
        "Short one. This is a longer trailing sentence with quite a few extra words in it today.\n\n"
        "# B\n\n"
        "Fresh start here.\n"
    )
    chunks = chunk_markdown(doc, max_tokens=6, overlap=2, heading_prefix=False)
    b_chunks = [c for c in chunks if c.heading_path == ["B"]]
    assert len(b_chunks) == 1
    assert b_chunks[0].body == "Fresh start here."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_tokens": 0, "overlap": 0},
        {"max_tokens": 10, "overlap": -1},
        {"max_tokens": 10, "overlap": 10},
    ],
)
def test_invalid_arguments_raise_value_error(kwargs):
    with pytest.raises(ValueError):
        chunk_markdown("# T\n\nSome text.\n", **kwargs)


def test_to_dict_and_jsonl_round_trip():
    doc = "# T\n\nOne. Two.\n"
    chunks = chunk_markdown(doc, max_tokens=512, overlap=0)
    rendered = chunks_to_jsonl(chunks)
    lines = rendered.splitlines()
    assert len(lines) == len(chunks)
    for line, chunk in zip(lines, chunks):
        record = json.loads(line)
        assert record == chunk.to_dict()
        assert set(record) == {
            "index",
            "text",
            "heading_path",
            "start_line",
            "end_line",
            "token_estimate",
        }
