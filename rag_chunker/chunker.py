import json
from collections import namedtuple
from dataclasses import dataclass, field

from .blocks import parse_blocks
from .sentences import split_sentences
from .tokens import estimate_tokens

_Piece = namedtuple("_Piece", ["text", "block", "atomic"])


@dataclass
class Chunk:
    index: int
    text: str
    body: str
    heading_path: list = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    token_estimate: int = 0
    oversized: bool = False

    def to_dict(self):
        return {
            "index": self.index,
            "text": self.text,
            "heading_path": self.heading_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_estimate": self.token_estimate,
        }


def chunk_markdown(text, max_tokens=512, overlap=64, heading_prefix=True):
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")

    blocks = parse_blocks(text)
    chunks = []
    for heading_path, section_blocks in _iter_sections(blocks):
        chunks.extend(
            _chunk_section(heading_path, section_blocks, max_tokens, overlap, heading_prefix)
        )

    for i, chunk in enumerate(chunks):
        chunk.index = i
    return chunks


def chunks_to_jsonl(chunks):
    return "\n".join(json.dumps(chunk.to_dict(), ensure_ascii=False) for chunk in chunks)


def _iter_sections(blocks):
    stack = []
    current_path = []
    current_blocks = []
    started = False

    for block in blocks:
        if block.type == "heading":
            if started:
                yield current_path, current_blocks
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            current_path = [entry[1] for entry in stack]
            current_blocks = []
            started = True
        else:
            started = True
            current_blocks.append(block)

    if started:
        yield current_path, current_blocks


def _build_pieces(blocks):
    pieces = []
    for block in blocks:
        if block.type == "paragraph":
            for sentence in split_sentences(block.text):
                pieces.append(_Piece(sentence, block, False))
        else:
            pieces.append(_Piece(block.text, block, True))
    return pieces


def _render(prefix, body):
    return f"{prefix}\n\n{body}" if prefix else body


def _body_of(carry, pieces):
    parts = ([carry] if carry else []) + [piece.text for piece in pieces]
    return "\n\n".join(part for part in parts if part)


def _tail_by_tokens(text, overlap_tokens):
    if overlap_tokens <= 0 or not text:
        return ""
    words = text.split()
    tail_words = []
    for word in reversed(words):
        candidate = " ".join([word] + tail_words)
        if tail_words and estimate_tokens(candidate) > overlap_tokens:
            break
        tail_words.insert(0, word)
    return " ".join(tail_words)


def _chunk_section(heading_path, blocks, max_tokens, overlap, heading_prefix):
    prefix = " > ".join(heading_path) if heading_prefix and heading_path else ""
    pieces = _build_pieces(blocks)
    if not pieces:
        return []

    results = []
    current = []
    carry = ""

    def flush(keep_overlap):
        nonlocal current, carry
        body = _body_of(carry, current)
        text_value = _render(prefix, body)
        token_estimate = estimate_tokens(text_value)
        oversized = token_estimate > max_tokens and any(
            piece.block.type in ("code", "table") for piece in current
        )
        results.append(
            Chunk(
                index=0,
                text=text_value,
                body=body,
                heading_path=list(heading_path),
                start_line=current[0].block.start_line,
                end_line=current[-1].block.end_line,
                token_estimate=token_estimate,
                oversized=oversized,
            )
        )
        carry = _tail_by_tokens(body, overlap) if keep_overlap and overlap > 0 else ""
        current = []

    for piece in pieces:
        if not current:
            current.append(piece)
            continue

        candidate_body = _body_of(carry, current + [piece])
        candidate_tokens = estimate_tokens(_render(prefix, candidate_body))

        if candidate_tokens <= max_tokens:
            current.append(piece)
        else:
            flush(keep_overlap=True)
            current.append(piece)

    flush(keep_overlap=False)
    return results
