import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_database as v

SE = {1: 0x140001000, 2: 0x140002000}


def test_clean_rows_pass():
    rows = [
        ["1", "0x140001000", "0x140009000", "4", "a"],
        ["2", "0x140002000", "0x14000a000", "3", "b"],
    ]
    assert v.check_database(rows, [], SE) == []


def test_each_database_defect_is_reported():
    rows = [
        ["2", "0x140002000", "0x14000a000", "9", "bad status"],
        ["1", "0x140001111", "0x14000a000", "4", "wrong se and shared vr"],
        ["1", "0x140001000", "0x1", "4", "dup id"],
    ]
    text = " | ".join(v.check_database(rows, [], SE))
    for needle in ("not ascending", "bad status", "SE address", "also used by id"):
        assert needle in text


def test_unchanged_rows_are_skipped_against_a_base():
    row = ["1", "0x140001111", "0x1", "4", "legacy"]
    assert v.check_database([row], [row], SE) == []


def test_se_ae_checks_aeid_and_order():
    assert (
        v.check_se_ae([["3", "9", "1", ""], ["5", "11", "1", ""]], [], {9: 1, 11: 2})
        == []
    )
    out = v.check_se_ae([["5", "11", "1", ""], ["3", "77", "1", ""]], [], {11: 2})
    assert any("not ascending" in p for p in out) and any("77" in p for p in out)


def test_load_offsets_adds_image_base():
    assert v.load_offsets("id,sse\n2,10d0\n") == {2: 0x1400010D0}


def test_unicode_digits_are_malformed_not_a_crash():
    rows = [["1", "0x140001000", "0x1", "4", "a"], ["\u00b2", "0x1", "0x2", "4", "b"]]
    assert any("malformed id" in p for p in v.check_database(rows, [], SE))
    out = v.check_se_ae([["3", "\u00b2", "1", ""]], [], {9: 1})
    assert any("malformed row" in p for p in out)
    assert v.load_offsets("id,sse\n\u00b2,10d0\n") == {}


def test_legacy_ordering_is_ignored_against_a_base():
    legacy = [
        ["5", "0x1", "0x10", "4", "a"],
        ["3", "0x2", "0x20", "4", "b"],
    ]
    se = {5: 1, 3: 2}
    assert v.check_database(legacy, legacy, se) == []
    changed = legacy + [["9", "0x3", "0x30", "4", "new"]]
    assert v.check_database(changed, legacy, {**se, 9: 3}) == []


def test_changed_row_out_of_order_is_reported_against_a_base():
    base = [["1", "0x1", "0x10", "4", "a"], ["5", "0x2", "0x20", "4", "b"]]
    rows = [base[0], ["7", "0x3", "0x30", "4", "x"], base[1]]
    assert any(
        "not ascending" in p for p in v.check_database(rows, base, {7: 3, 1: 1, 5: 2})
    )
    dup = base + [["5", "0x2", "0x21", "4", "again"]]
    assert any("duplicates [5]" in p for p in v.check_database(dup, base, {5: 2, 1: 1}))
    assert any(
        "not ascending" in p
        for p in v.check_se_ae(
            [["1", "9", "1", ""], ["0", "9", "1", ""]], [["1", "9", "1", ""]], {9: 1}
        )
    )


def test_bad_base_ref_is_an_error_not_an_empty_base():
    with pytest.raises(RuntimeError, match="git show"):
        v._git_show("no-such-ref-for-verifier-test", "database.csv")
    assert v.main(["--base", "no-such-ref-for-verifier-test"]) == 2


def test_unchanged_malformed_id_is_skipped_against_a_base():
    bad = ["x", "0x1", "0x2", "4", "legacy"]
    assert v.check_database([bad], [bad], SE) == []
    assert v.check_se_ae([["x", "9", "1", ""]], [["x", "9", "1", ""]], {9: 1}) == []
    assert any("malformed id" in p for p in v.check_database([bad], [], SE))


def test_extra_identical_copy_counts_as_changed():
    row = ["1", "0x140001000", "0x9", "4", "a"]
    out = v.check_database([row, row], [row], SE)
    assert any("duplicates [1]" in p for p in out)
    se_ae = ["3", "77", "1", ""]
    out = v.check_se_ae([se_ae, se_ae], [se_ae], {})
    assert any("not ascending" in p for p in out) and any("77" in p for p in out)
