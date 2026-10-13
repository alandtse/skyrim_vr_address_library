"""Static consistency checks for database.csv and se_ae.csv.

Checks, on the rows that differ from --base (every row when --base is omitted):
  database.csv  5 columns, status 0-4, ids ascending and unique, SE address equal to
                offsets-1.5.97.0.csv, VR address not already used by another id
  se_ae.csv     ids ascending and unique, aeid present in offsets-1-6-1170.0.csv

Usage: python scripts/verify_database.py [--base REF]
Exits 1 when any problem is found, 2 when --base cannot be read. Ghidra-backed checks (status 4 byte equality) are out of scope.
"""

import argparse
import csv
import io
import subprocess
import sys
from collections import Counter, defaultdict

IMAGE_BASE = 0x140000000


def _is_number(text):
    return text.isascii() and text.isdigit()


def parse_rows(text):
    return [
        r
        for r in list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))[1:]
        if r and r[0].strip()
    ]


def load_offsets(text):
    return {
        int(r[0]): int(r[1], 16) + IMAGE_BASE
        for r in parse_rows(text)
        if _is_number(r[0]) and len(r) >= 2 and r[1]
    }


def _changed_flags(rows, base_rows):
    """True for rows not matched by a base row; each base row matches one copy."""
    remaining = Counter(tuple(r) for r in base_rows)
    flags = []
    for r in rows:
        key = tuple(r)
        if remaining[key] > 0:
            remaining[key] -= 1
            flags.append(False)
        else:
            flags.append(True)
    return flags


def _numeric_id_rows(rows, changed, problems):
    """Rows with a numeric id and their changed flags; changed others are reported."""
    kept, kept_changed = [], []
    for r, c in zip(rows, changed, strict=True):
        if _is_number(r[0]):
            kept.append(r)
            kept_changed.append(c)
        elif c:
            problems.append("malformed id %r" % r[0])
    return kept, kept_changed


def _order_problem(ids, changed):
    """Duplicate ids and out-of-order neighbours that involve a changed row."""
    counts = Counter(ids)
    dups = sorted({i for i, c in zip(ids, changed, strict=True) if c and counts[i] > 1})
    misordered = any(
        c and ((k > 0 and ids[k - 1] >= i) or (k + 1 < len(ids) and i >= ids[k + 1]))
        for k, (i, c) in enumerate(zip(ids, changed, strict=True))
    )
    return dups, misordered


def check_database(rows, base_rows, se_offsets):
    """Problems in `rows`; only rows that differ from `base_rows` get per-row checks."""
    problems = []
    rows, changed = _numeric_id_rows(rows, _changed_flags(rows, base_rows), problems)
    ids = [int(r[0]) for r in rows]
    dups, misordered = _order_problem(ids, changed)
    if dups or misordered:
        problems.append(
            "ids not ascending and unique" + (" (duplicates %s)" % dups if dups else "")
        )
    by_vr = defaultdict(list)
    for r in rows:
        if len(r) == 5:
            try:
                by_vr[int(r[2], 16)].append(int(r[0]))
            except ValueError:
                pass
    for r, is_changed in zip(rows, changed, strict=True):
        if not is_changed:
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
    rows, changed = _numeric_id_rows(rows, _changed_flags(rows, base_rows), problems)
    ids = [int(r[0]) for r in rows]
    if any(_order_problem(ids, changed)):
        problems.append("sseids not ascending and unique")
    for r, is_changed in zip(rows, changed, strict=True):
        if not is_changed:
            continue
        if len(r) < 2 or not _is_number(r[1]):
            problems.append("%s: malformed row" % r[0])
        elif int(r[1]) not in ae_offsets:
            problems.append(
                "%s->%s: aeid absent from AE 1.6.1170 offsets" % (r[0], r[1])
            )
    return problems


def _git_show(ref, path):
    p = subprocess.run(["git", "show", "%s:%s" % (ref, path)], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(
            "git show %s:%s failed: %s"
            % (ref, path, p.stderr.decode("utf-8", "replace").strip())
        )
    return p.stdout.decode("utf-8")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="git ref; only rows that differ from it are checked")
    args = ap.parse_args(argv)
    try:
        base_db = parse_rows(_git_show(args.base, "database.csv")) if args.base else []
        base_sa = parse_rows(_git_show(args.base, "se_ae.csv")) if args.base else []
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2
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
