"""Planner University Core rules: GE China Programme (UGEA1555) and the GE
Foundation Programme transition (2-unit UGFH1002 / UGFN1002).

`app.planner._compute_ucore` is a pure function of the saved rows plus the
loaded catalogue, so these tests need no Streamlit runtime: conftest.py stubs
supabase and binds st.secrets, and load_all_data() reads the real data/ files.
"""

import pytest

from app.planner import (
    _compute_ucore,
    _compute_ucore_detail,
    _foundation_credits,
    _foundation_taken_credits,
    _ge_china_credits,
)
from src.data_retrieval import load_all_data

_FOUR_AREA = "GE: Four Areas (Area A, C, D)"
_FOUNDATION = "GE: Foundation Courses"
_CHINA = "Understanding China"


@pytest.fixture(scope="module")
def context():
    return load_all_data()


def _plan(*course_ids : str) -> list[dict]:
    """Rows shaped like fetch_all_planned output (catalogue rows, no DB credits)."""
    return [{"course_id": cid, "source": "study_plan", "credits": 0} for cid in course_ids]


def _area(credits : int) -> dict:
    """A free-entry Four-Area row (credits are user-typed)."""
    return {"course_id": "UGEA1000", "source": "four_area_ge", "credits": credits}


class TestChinaProgramme:
    """UGEA1555 special option: 3 units of Area A, or UGCP1001 + 2 units."""

    def test_china_core_alone(self):
        assert _ge_china_credits(_plan("UGCP1001")) == (1, 0)

    def test_ugcp1003_counts_as_china_core(self):
        assert _ge_china_credits(_plan("UGCP1003")) == (1, 0)

    def test_ugea1555_substitutes_for_ugcp1001(self):
        assert _ge_china_credits(_plan("UGEA1555")) == (1, 2)

    def test_ugea1555_is_area_only_when_china_core_planned(self):
        assert _ge_china_credits(_plan("UGCP1001", "UGEA1555")) == (1, 3)
        assert _ge_china_credits(_plan("UGCP1003", "UGEA1555")) == (1, 3)

    def test_ugea1555_in_free_entry_table_is_not_special(self):
        rows = [{"course_id": "UGEA1555", "source": "four_area_ge", "credits": 3}]
        assert _ge_china_credits(rows) == (0, 0)


class TestFoundationProgramme:
    """1002 courses are 2 units; each missing unit becomes a Four-Area unit."""

    def test_three_unit_pair_needs_no_makeup(self, context):
        rows = _plan("UGFH1000", "UGFN1000")
        assert _foundation_credits(context, rows) == (True, 0)

    def test_two_unit_pair_needs_two_area_units(self, context):
        rows = _plan("UGFH1002", "UGFN1002")
        assert _foundation_credits(context, rows) == (True, 2)

    def test_mixed_pair_needs_one_area_unit(self, context):
        rows = _plan("UGFH1000", "UGFN1002")
        assert _foundation_credits(context, rows) == (True, 1)

    def test_missing_side_is_not_substitutable(self, context):
        rows = _plan("UGFH1002")
        assert _foundation_credits(context, rows) == (False, 1)

    def test_area_table_has_no_foundation_courses(self, context):
        rows = [{"course_id": "UGFH1000", "source": "four_area_ge", "credits": 3}]
        assert _foundation_credits(context, rows) == (False, 0)


class TestComputeUcore:
    """End-to-end status flags for the two transitional rules."""

    def test_ugea1555_alone_fulfils_china_but_not_four_areas(self, context):
        status = _compute_ucore(context, _plan("UGEA1555"))
        assert status[_CHINA] is True
        assert status[_FOUR_AREA] is False  # only 2 Area-A units

    def test_ugea1555_adds_two_area_units_without_china_core(self, context):
        status = _compute_ucore(context, _plan("UGEA1555") + [_area(4)])
        assert status[_CHINA] is True
        assert status[_FOUR_AREA] is True  # 4 + 2 = 6

    def test_ugea1555_adds_three_area_units_with_china_core(self, context):
        status = _compute_ucore(context, _plan("UGCP1001", "UGEA1555") + [_area(3)])
        assert status[_CHINA] is True
        assert status[_FOUR_AREA] is True  # 3 + 3 = 6

    def test_two_unit_foundation_raises_four_area_requirement(self, context):
        rows = _plan("UGFH1002", "UGFN1002") + [_area(6)]
        status = _compute_ucore(context, rows)
        assert status[_FOUNDATION] is True
        assert status[_FOUR_AREA] is False  # 6 < 6 + 2 make-up units

    def test_two_unit_foundation_passes_with_makeup_credits(self, context):
        rows = _plan("UGFH1002", "UGFN1002") + [_area(8)]
        status = _compute_ucore(context, rows)
        assert status[_FOUNDATION] is True
        assert status[_FOUR_AREA] is True  # 8 >= 6 + 2

    def test_three_unit_foundation_keeps_six_area_units(self, context):
        rows = _plan("UGFH1000", "UGFN1000") + [_area(6)]
        status = _compute_ucore(context, rows)
        assert status[_FOUNDATION] is True
        assert status[_FOUR_AREA] is True

    def test_mixed_foundation_needs_seven_area_units(self, context):
        status = _compute_ucore(context, _plan("UGFH1000", "UGFN1002") + [_area(6)])
        assert status[_FOUNDATION] is True
        assert status[_FOUR_AREA] is False  # 6 < 6 + 1 make-up unit
        status = _compute_ucore(context, _plan("UGFH1000", "UGFN1002") + [_area(7)])
        assert status[_FOUR_AREA] is True

    def test_missing_foundation_side_fails(self, context):
        status = _compute_ucore(context, _plan("UGFH1000"))
        assert status[_FOUNDATION] is False


class TestUcoreCredits:
    """Credits column of the University Core table (planned credits, not capped)."""

    def test_foundation_credits_two_unit_pair(self, context):
        detail = _compute_ucore_detail(context, _plan("UGFH1002", "UGFN1002"))
        assert detail[_FOUNDATION] == [True, 4]

    def test_foundation_credits_mixed_pair(self, context):
        detail = _compute_ucore_detail(context, _plan("UGFH1000", "UGFN1002"))
        assert detail[_FOUNDATION] == [True, 5]

    def test_foundation_credits_three_unit_pair(self, context):
        detail = _compute_ucore_detail(context, _plan("UGFH1000", "UGFN1000"))
        assert detail[_FOUNDATION] == [True, 6]

    def test_foundation_taken_credits_uses_largest_version_per_side(self, context):
        rows = _plan("UGFH1000", "UGFH1002", "UGFN1002")
        assert _foundation_taken_credits(context, rows) == 5  # 3 + 2

    def test_chinese_credits(self, context):
        detail = _compute_ucore_detail(context, _plan("CHLT1001", "CHLT1002"))
        assert detail["Chinese Language"] == [True, 5]

    def test_english_credits_are_uncapped(self, context):
        rows = [
            {"course_id": "ELTU1001", "source": "english", "credits": 0},
            {"course_id": "ELTU2011", "source": "english", "credits": 0},
            {"course_id": "ELTU2012", "source": "english", "credits": 0},
        ]
        detail = _compute_ucore_detail(context, rows)
        assert detail["English Language"] == [True, 9]  # 3 + 3 + 3, above the 8-unit target

    def test_ugea1555_credit_split(self, context):
        detail = _compute_ucore_detail(context, _plan("UGEA1555"))
        assert detail[_CHINA] == [True, 1]
        assert detail[_FOUR_AREA] == [False, 2]

    def test_ugea1555_area_credits_with_china_core(self, context):
        detail = _compute_ucore_detail(context, _plan("UGCP1001", "UGEA1555"))
        assert detail[_CHINA] == [True, 1]
        assert detail[_FOUR_AREA] == [False, 3]

    def test_input_table_credits(self, context):
        rows = [
            {"course_id": "PED1001", "source": "pe", "credits": 2},
            {"course_id": "GEC1001", "source": "college_ge", "credits": 6},
            _area(6),
        ]
        detail = _compute_ucore_detail(context, rows)
        assert detail["Physical Education"] == [True, 2]
        assert detail["College GE"] == [True, 6]
        assert detail[_FOUR_AREA] == [True, 6]

    def test_over_taken_input_credits_are_not_capped(self, context):
        detail = _compute_ucore_detail(
            context, [{"course_id": "PED1001", "source": "pe", "credits": 3}]
        )
        assert detail["Physical Education"] == [True, 3]

    def test_catalogue_specific_course_credits(self, context):
        detail = _compute_ucore_detail(context, _plan("UGCP1002", "ENGG1003"))
        assert detail["Hong Kong in the Wider Constitutional Order"] == [True, 1]
        assert detail["Digital Literacy and Computational Thinking"] == [True, 3]

    def test_ucore_wrapper_matches_detail_flags(self, context):
        rows = _plan("UGFH1002", "UGFN1002", "UGEA1555", "UGCP1002", "ENGG1003") + [_area(4)]
        flags = _compute_ucore(context, rows)
        detail = _compute_ucore_detail(context, rows)
        assert flags == {item: value[0] for item, value in detail.items()}
