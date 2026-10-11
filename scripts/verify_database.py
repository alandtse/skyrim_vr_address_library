"""Static consistency checks for database.csv and se_ae.csv.

Checks, on the rows that differ from --base (every row when --base is omitted):
  database.csv  5 columns, status 0-4, ids ascending and unique, SE address equal to
                offsets-1.5.97.0.csv, VR address not already used by another id
  se_ae.csv     ids ascending and unique, aeid present in offsets-1-6-1170.0.csv

Usage: python scripts/verify_database.py [--base REF]
Exits 1 when any problem is found. Ghidra-backed checks (status 4 byte equality) are out of scope.
"""

import argparse
import csv
import io
import subprocess
import sys
from collections import Counter, defaultdict

IMAGE_BASE = 0x140000000


def parse_rows(text):
    return [
        r
        for r in list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))[1:]
        if r and r[0].isdigit()
    ]


def load_offsets(text):
    return {
        int(r[0]): int(r[1], 16) + IMAGE_BASE
        for r in parse_rows(text)
        if len(r) >= 2 and r[1]
    }


def _unordered(ids):
    return ids != sorted(ids) or len(set(ids)) != len(ids)


def check_database(rows, base_rows, se_offsets):
    """Problems in `rows`; only rows that differ from `base_rows` get per-row checks."""
    problems = []
    ids = [int(r[0]) for r in rows]
    if _unordered(ids):
        dups = sorted(i for i, n in Counter(ids).items() if n > 1)
        problems.append(
            "ids not ascending and unique" + (" (duplicates %s)" % dups if dups else "")
        )
    base = {tuple(r) for r in base_rows}
    by_vr = defaultdict(list)
    for r in rows:
        if len(r) == 5:
            try:
                by_vr[int(r[2], 16)].append(int(r[0]))
            except ValueError:
                pass
    for r in rows:
        if tuple(r) in base:
            continue
        i = int(r[0])
        if len(r) != 5:
            problems.append("%d: %d columns, expected 5" % (i, len(r)))
            continue
        try:
            sse, vr = int(r[1], 16), int(r[2], 16)
        except ValueError:
            problems.append("%d: address is not hex (%s, %s)" % (i, r[1], r[2]))
            continue
        if r[3] not in ("0", "1", "2", "3", "4"):
            problems.append("%d: bad status %r" % (i, r[3]))
        want = se_offsets.get(i)
        if want is not None and want != sse:
            problems.append("%d: SE address %#x != offsets table %#x" % (i, sse, want))
        clash = [j for j in by_vr[vr] if j != i]
        if clash:
            problems.append("%d: VR address %#x also used by id %s" % (i, vr, clash))
    return problems


def check_se_ae(rows, base_rows, ae_offsets):
    problems = []
    ids = [int(r[0]) for r in rows]
    if _unordered(ids):
        problems.append("sseids not ascending and unique")
    base = {tuple(r) for r in base_rows}
    for r in rows:
        if tuple(r) in base:
            continue
        if len(r) < 2 or not r[1].isdigit():
            problems.append("%s: malformed row" % r[0])
        elif int(r[1]) not in ae_offsets:
            problems.append(
                "%s->%s: aeid absent from AE 1.6.1170 offsets" % (r[0], r[1])
            )
    return problems


def _git_show(ref, path):
    p = subprocess.run(["git", "show", "%s:%s" % (ref, path)], capture_output=True)
    return p.stdout.decode("utf-8") if p.returncode == 0 else ""


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="git ref; only rows that differ from it are checked")
    args = ap.parse_args(argv)
    base_db = parse_rows(_git_show(args.base, "database.csv")) if args.base else []
    base_sa = parse_rows(_git_show(args.base, "se_ae.csv")) if args.base else []
    problems = [
        ("database.csv", p)
        for p in check_database(
            parse_rows(_read("database.csv")),
            base_db,
            load_offsets(_read("offsets-1.5.97.0.csv")),
        )
    ]
    problems += [
        ("se_ae.csv", p)
        for p in check_se_ae(
            parse_rows(_read("se_ae.csv")),
            base_sa,
            load_offsets(_read("offsets-1-6-1170.0.csv")),
        )
    ]
    for f, p in problems:
        print("%s: %s" % (f, p))
    print("%d problem(s)" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
