"""
Command-line tool: try the library without writing code.

    misheard Barmer बाड़मेर                  # distance and the steps behind it
    misheard --refs places.txt Baadmer       # closest references
    cat heard.txt | misheard --refs places.txt

Also runs as `python -m misheard`.
"""
import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .distance import Confusions
from .explain import explain
from .match import Matcher, Reference


def _read_refs(path: str) -> list[Reference]:
    """One reference per line; `key<TAB>text` groups aliases under a key. # starts a comment."""
    refs: list[Reference] = []
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    with stream:
        for line in stream:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" in line:
                key, text = line.split("\t", 1)
                refs.append((key.strip(), text.strip()))
            else:
                refs.append(line.strip())
    return refs


def _print_matches(heard: str, matches, out, show_heard: bool) -> None:
    if show_heard:
        print(heard, file=out)
    if not matches:
        print("  (no match)", file=out)
    width = max((len(m.text) for m in matches), default=0)
    for m in matches:
        key = f"  [{m.key}]" if m.key != m.text else ""
        print(f"  {m.distance:6.2f}  {m.text:<{width}}{key}".rstrip(), file=out)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="misheard",
        description="Match Indian names and places by how they sound.",
        epilog="examples:\n"
               "  misheard Barmer बाड़मेर\n"
               "  misheard --refs places.txt Baadmer Chenai\n"
               "  cat heard.txt | misheard --refs places.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("names", nargs="*", metavar="NAME",
                   help="two names to compare, or with --refs, what was heard")
    p.add_argument("-r", "--refs", metavar="FILE",
                   help="reference list, one per line (key<TAB>text for aliases); - for stdin")
    p.add_argument("-n", "--top", type=int, default=3, metavar="N", help="matches to show with --refs (default 3)")
    p.add_argument("-c", "--confusions", metavar="CSV", action="append", default=[],
                   help="extra confusion rows (a,b,cost,why), merged over the defaults; repeatable")
    p.add_argument("--no-default-confusions", action="store_true",
                   help="start from an empty confusion table instead of the default one")
    p.add_argument("-q", "--quiet", action="store_true", help="print only the distance(s)")
    p.add_argument("-V", "--version", action="version", version=f"misheard {__version__}")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    out = sys.stdout

    try:
        table = Confusions() if args.no_default_confusions else Confusions.default()
        for path in args.confusions:
            table = table.merged(Confusions.from_csv(path))

        if args.refs:
            if args.top < 1:
                parser.error("--top must be at least 1")
            if args.refs == "-" and not args.names:
                parser.error("with --refs -, give what was heard as arguments")
            matcher = Matcher(_read_refs(args.refs), confusions=table)
            heard = args.names or [line.strip() for line in sys.stdin if line.strip()]
            for i, h in enumerate(heard):
                matches = matcher.best_match(h, args.top)
                if args.quiet:
                    print(f"{matches[0].distance:g}\t{matches[0].text}" if matches else "inf\t", file=out)
                    continue
                if i:
                    print(file=out)
                _print_matches(h, matches, out, show_heard=True)
            return 0

        if len(args.names) != 2:
            parser.error("give two names to compare, or --refs FILE")
        e = explain(*args.names, confusions=table)
        print(f"{e.distance:g}" if args.quiet else e, file=out)
        return 0
    except (OSError, ValueError) as err:        # bad file, bad CSV row, unsupported script
        print(f"misheard: error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
