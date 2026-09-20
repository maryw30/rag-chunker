import re
from dataclasses import dataclass

from .tokens import estimate_tokens

_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:\s+(.*?))?\s*$")
_LIST_ITEM_RE = re.compile(r"^\s{0,3}([-*+]|\d+[.)])\s+")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


@dataclass
class Block:
    type: str
    text: str
    start_line: int
    end_line: int
    level: int = 0


def parse_blocks(text):
    lines = text.splitlines()
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = (heading_match.group(2) or "").rstrip("#").strip()
            blocks.append(Block("heading", heading_text, i + 1, i + 1, level))
            i += 1
            continue

        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            blocks.append(_parse_code_block(lines, i, n))
            i = blocks[-1].end_line
            continue

        if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            start = i
            i += 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                i += 1
            blocks.append(Block("table", "\n".join(lines[start:i]), start + 1, i, 0))
            continue

        if _LIST_ITEM_RE.match(line):
            start = i
            i += 1
            while i < n and lines[i].strip() and (
                _LIST_ITEM_RE.match(lines[i]) or lines[i][:1] in (" ", "\t")
            ):
                i += 1
            blocks.append(Block("list", "\n".join(lines[start:i]), start + 1, i, 0))
            continue

        start = i
        i += 1
        while i < n and lines[i].strip() and not _starts_new_block(lines, i, n):
            i += 1
        blocks.append(Block("paragraph", "\n".join(lines[start:i]), start + 1, i, 0))

    return blocks


def _starts_new_block(lines, i, n):
    line = lines[i]
    stripped = line.strip()
    if _HEADING_RE.match(line):
        return True
    if stripped.startswith("```") or stripped.startswith("~~~"):
        return True
    if _LIST_ITEM_RE.match(line):
        return True
    if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
        return True
    return False


def split_list_items(block):
    # continuation lines (indented text under an item) stay attached to that item
    lines = block.text.splitlines()
    boundaries = [i for i, line in enumerate(lines) if _LIST_ITEM_RE.match(line)]
    if not boundaries:
        return [block]

    items = []
    line_no = block.start_line
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        item_lines = lines[start:end]
        items.append(Block("list", "\n".join(item_lines), line_no, line_no + len(item_lines) - 1, 0))
        line_no += len(item_lines)
    return items


def split_table_rows(block):
    # each piece repeats the header and separator so a lone row is still
    # readable on its own, the way split_list_items keeps continuation lines
    # attached to their item
    if block.type != "table":
        return [block]
    lines = block.text.splitlines()
    if len(lines) < 3:
        return [block]

    header, separator = lines[0], lines[1]
    data_rows = lines[2:]
    row_line = block.start_line + 2
    items = []
    for row in data_rows:
        text = "\n".join([header, separator, row])
        items.append(Block("table", text, block.start_line, row_line, 0))
        row_line += 1
    return items


def split_code_lines(block, max_tokens):
    # a code block is normally kept whole; only break it up when it can't
    # possibly fit in a chunk on its own, and even then keep it fenced so
    # each piece still renders as valid code by itself
    if block.type != "code" or max_tokens <= 0:
        return [block]
    if estimate_tokens(block.text) <= max_tokens:
        return [block]

    lines = block.text.splitlines()
    if len(lines) < 3:
        return [block]

    open_line = lines[0]
    fence_char = open_line.strip()[0]
    fence_len = len(open_line.strip()) - len(open_line.strip().lstrip(fence_char))
    last_stripped = lines[-1].strip()
    closed = len(last_stripped) >= fence_len and set(last_stripped) == {fence_char}
    body_lines = lines[1:-1] if closed else lines[1:]
    close_line = lines[-1] if closed else fence_char * max(fence_len, 3)

    if len(body_lines) < 2:
        return [block]

    pieces = []
    current = []
    current_start = block.start_line + 1

    def flush(end_line):
        text = "\n".join([open_line] + current + [close_line])
        pieces.append(Block("code", text, current_start, end_line, 0))

    line_no = current_start
    for line in body_lines:
        trial = current + [line]
        trial_text = "\n".join([open_line] + trial + [close_line])
        if current and estimate_tokens(trial_text) > max_tokens:
            flush(line_no - 1)
            current = [line]
            current_start = line_no
        else:
            current.append(line)
        line_no += 1

    flush(line_no - 1)
    return pieces if len(pieces) > 1 else [block]


def _parse_code_block(lines, start, n):
    fence_char = lines[start].strip()[0]
    fence_len = len(lines[start].strip()) - len(lines[start].strip().lstrip(fence_char))
    i = start + 1
    closed = False
    while i < n:
        candidate = lines[i].strip()
        if len(candidate) >= fence_len and set(candidate) == {fence_char}:
            i += 1
            closed = True
            break
        i += 1
    end = i if closed else n
    return Block("code", "\n".join(lines[start:end]), start + 1, end, 0)
