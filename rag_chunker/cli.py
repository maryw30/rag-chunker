import argparse
import json
import sys

from .chunker import chunk_markdown, chunks_to_jsonl


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rag-chunker",
        description="Structure-aware markdown chunking for retrieval pipelines.",
    )
    parser.add_argument("input", help='markdown file to chunk, or "-" for stdin')
    parser.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument(
        "--no-heading-prefix", action="store_false", dest="heading_prefix", default=True
    )
    parser.add_argument("--array", action="store_true")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("-o", "--output", dest="output", default=None)
    return parser


def _read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _print_stats(chunks):
    if not chunks:
        print("0 chunks", file=sys.stderr)
        return
    tokens = [chunk.token_estimate for chunk in chunks]
    oversized = sum(1 for chunk in chunks if chunk.oversized)
    average = round(sum(tokens) / len(tokens))
    print(
        f"{len(chunks)} chunks | tokens min {min(tokens)} avg {average} "
        f"max {max(tokens)} | {oversized} oversized",
        file=sys.stderr,
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.input)
    except OSError as exc:
        parser.error(f"cannot read {args.input}: {exc.strerror}")

    try:
        chunks = chunk_markdown(
            text,
            max_tokens=args.max_tokens,
            overlap=args.overlap,
            heading_prefix=args.heading_prefix,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.array:
        rendered = json.dumps([chunk.to_dict() for chunk in chunks], indent=2)
    else:
        rendered = chunks_to_jsonl(chunks)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.write("\n")
    else:
        sys.stdout.write(rendered)
        sys.stdout.write("\n")

    if args.stats:
        _print_stats(chunks)

    return 0


if __name__ == "__main__":
    sys.exit(main())
