import io
import json
import sys

import pytest

from rag_chunker.chunker import chunk_markdown, chunks_to_jsonl
from rag_chunker.cli import build_parser, main

DOC = "# Title\n\nOne. Two.\n\n## Sub\n\nThree words here today.\n"


def test_build_parser_defaults():
    args = build_parser().parse_args(["doc.md"])
    assert args.input == "doc.md"
    assert args.max_tokens == 512
    assert args.overlap == 64
    assert args.heading_prefix is True
    assert args.array is False
    assert args.stats is False
    assert args.output is None


def test_no_heading_prefix_flag_disables_prefix():
    args = build_parser().parse_args(["doc.md", "--no-heading-prefix"])
    assert args.heading_prefix is False


def test_main_writes_jsonl_matching_the_library_output(tmp_path, capsys):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text(DOC, encoding="utf-8")

    exit_code = main([str(doc_path), "--max-tokens", "20", "--overlap", "0"])

    expected = chunks_to_jsonl(chunk_markdown(DOC, max_tokens=20, overlap=0))
    out = capsys.readouterr().out
    assert exit_code == 0
    assert out == expected + "\n"


def test_main_array_flag_emits_a_json_array(tmp_path, capsys):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text(DOC, encoding="utf-8")

    main([str(doc_path), "--array"])

    parsed = json.loads(capsys.readouterr().out)
    assert isinstance(parsed, list)
    assert parsed == [chunk.to_dict() for chunk in chunk_markdown(DOC)]


def test_main_writes_to_output_file_instead_of_stdout(tmp_path, capsys):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text(DOC, encoding="utf-8")
    out_path = tmp_path / "out.jsonl"

    main([str(doc_path), "-o", str(out_path)])

    assert capsys.readouterr().out == ""
    expected = chunks_to_jsonl(chunk_markdown(DOC))
    assert out_path.read_text(encoding="utf-8") == expected + "\n"


def test_main_stats_go_to_stderr_not_stdout(tmp_path, capsys):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text(DOC, encoding="utf-8")

    main([str(doc_path), "--stats"])

    captured = capsys.readouterr()
    assert "chunks" in captured.err
    assert "oversized" in captured.err
    assert captured.out != ""


def test_main_reads_stdin_when_input_is_a_dash(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(DOC))

    main(["-"])

    expected = chunks_to_jsonl(chunk_markdown(DOC))
    assert capsys.readouterr().out == expected + "\n"


def test_main_errors_on_missing_file(capsys):
    with pytest.raises(SystemExit):
        main(["/no/such/path/does-not-exist.md"])
    assert "cannot read" in capsys.readouterr().err


def test_main_errors_when_overlap_is_not_smaller_than_max_tokens(tmp_path, capsys):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text(DOC, encoding="utf-8")

    with pytest.raises(SystemExit):
        main([str(doc_path), "--max-tokens", "10", "--overlap", "10"])
    assert "overlap must be smaller than max_tokens" in capsys.readouterr().err
