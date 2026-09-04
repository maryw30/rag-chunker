from rag_chunker.blocks import Block, parse_blocks, split_list_items


def test_heading_strips_trailing_hashes():
    blocks = parse_blocks("## Foo ##\n")
    assert blocks == [Block("heading", "Foo", 1, 1, 2)]


def test_heading_with_no_text():
    blocks = parse_blocks("###\n")
    assert blocks == [Block("heading", "", 1, 1, 3)]


def test_code_block_closed():
    text = "```python\nprint('hi')\n```\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.type == "code"
    assert block.start_line == 1
    assert block.end_line == 3
    assert block.text == "```python\nprint('hi')\n```"


def test_code_block_unterminated_runs_to_end_of_document():
    text = "```\nno closing fence here\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.type == "code"
    assert block.start_line == 1
    assert block.end_line == 2


def test_table_block_requires_separator_row():
    text = "| a | b |\n| -- | -- |\n| 1 | 2 |\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.type == "table"
    assert block.start_line == 1
    assert block.end_line == 3


def test_pipe_without_separator_row_is_a_paragraph():
    text = "a | b\nnot a table\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].type == "paragraph"


def test_list_block_groups_consecutive_items():
    text = "- item one\n- item two\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.type == "list"
    assert block.start_line == 1
    assert block.end_line == 2


def test_ordered_list_item_marker():
    blocks = parse_blocks("1. first\n2) second\n")
    assert len(blocks) == 1
    assert blocks[0].type == "list"


def test_paragraph_block_joins_consecutive_lines():
    text = "This is a paragraph\nthat spans two lines.\n\nNext paragraph.\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 2
    first, second = blocks
    assert first.type == "paragraph"
    assert first.text == "This is a paragraph\nthat spans two lines."
    assert first.start_line == 1
    assert first.end_line == 2
    assert second.type == "paragraph"
    assert second.text == "Next paragraph."
    assert second.start_line == 4
    assert second.end_line == 4


def test_multiple_blank_lines_between_blocks_are_skipped():
    blocks = parse_blocks("A\n\n\n\nB\n")
    assert blocks == [
        Block("paragraph", "A", 1, 1, 0),
        Block("paragraph", "B", 5, 5, 0),
    ]


def test_paragraph_stops_at_a_following_heading():
    blocks = parse_blocks("Paragraph text.\n# Heading\n")
    assert len(blocks) == 2
    assert blocks[0].type == "paragraph"
    assert blocks[1].type == "heading"


def test_empty_document_has_no_blocks():
    assert parse_blocks("") == []
    assert parse_blocks("\n\n\n") == []


def test_split_list_items_gives_one_block_per_item_with_correct_lines():
    text = "- item one\n- item two\n- item three\n"
    block = parse_blocks(text)[0]
    items = split_list_items(block)
    assert [item.text for item in items] == ["- item one", "- item two", "- item three"]
    assert [(item.start_line, item.end_line) for item in items] == [(1, 1), (2, 2), (3, 3)]
    assert all(item.type == "list" for item in items)


def test_split_list_items_keeps_continuation_lines_with_their_item():
    text = "- item one\n  continued text\n- item two\n"
    block = parse_blocks(text)[0]
    items = split_list_items(block)
    assert items[0].text == "- item one\n  continued text"
    assert items[0].start_line == 1
    assert items[0].end_line == 2
    assert items[1].text == "- item two"
    assert items[1].start_line == 3
    assert items[1].end_line == 3


def test_split_list_items_on_non_list_block_returns_it_unchanged():
    block = parse_blocks("Just a paragraph.\n")[0]
    assert split_list_items(block) == [block]
