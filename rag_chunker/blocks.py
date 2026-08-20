import re
from dataclasses import dataclass

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
