import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_database as v  # noqa: E402

SE = {1: 0x140001000, 2: 0x140002000}


def test_clean_rows_pass():
    rows = [['1', '0x140001000', '0x140009000', '4', 'a'], ['2', '0x140002000', '0x14000a000', '3', 'b']]
    assert v.check_database(rows, [], SE) == []


def test_each_database_defect_is_reported():
    rows = [['2', '0x140002000', '0x14000a000', '9', 'bad status'],
            ['1', '0x140001111', '0x14000a000', '4', 'wrong se and shared vr'],
            ['1', '0x140001000', '0x1', '4', 'dup id']]
    text = ' | '.join(v.check_database(rows, [], SE))
    for needle in ('not ascending', 'bad status', 'SE address', 'also used by id'):
        assert needle in text


def test_unchanged_rows_are_skipped_against_a_base():
    row = ['1', '0x140001111', '0x1', '4', 'legacy']
    assert v.check_database([row], [row], SE) == []


def test_se_ae_checks_aeid_and_order():
    assert v.check_se_ae([['3', '9', '1', ''], ['5', '11', '1', '']], [], {9: 1, 11: 2}) == []
    out = v.check_se_ae([['5', '11', '1', ''], ['3', '77', '1', '']], [], {11: 2})
    assert any('not ascending' in p for p in out) and any('77' in p for p in out)


def test_load_offsets_adds_image_base():
    assert v.load_offsets('id,sse\n2,10d0\n') == {2: 0x1400010D0}
