"""Tests for data_retrieval.py and storage.py — pure functions, data integrity,
and the study-period persistence contract (canonical course key)."""

import pandas as pd
import pytest
import streamlit as st

from src.data_retrieval import (
    determine_campus,
    load_all_data,
    get_course_info,
    get_course_list,
    get_equivalence_courses,
    get_major_2_requirement,
    get_course_id_list,
    convert_course_id,
    DataLoadError,
    InfoMissingError,
    _course_key,
    show_course_info,
)


class TestDetermineCampus:
    def test_hk_campus(self):
        assert determine_campus("MATH1010") == "hk"

    def test_sz_campus(self):
        assert determine_campus("DDA1001") == "sz"

    def test_borderline_7_chars_hk(self):
        assert determine_campus("ABCX123") == "hk"

    def test_borderline_7_chars_sz(self):
        assert determine_campus("ABC1123") == "sz"

    def test_short_id_raises(self):
        with pytest.raises(DataLoadError):
            determine_campus("ABC")


class TestDataLoading:
    @pytest.fixture(scope="class")
    def context(self):
        return load_all_data()

    def test_course_info_not_empty(self, context):
        assert len(context.course_info) > 0

    def test_course_info_structure(self, context):
        for code, info in context.course_info.items():
            assert isinstance(code, str)
            assert isinstance(info, list)
            assert len(info) == 2

    def test_course_list_has_majors(self, context):
        assert "Interdisciplinary Data Analytics" in context.course_list

    def test_equivalence_courses_not_empty(self, context):
        assert len(context.equivalence_courses) > 0

    def test_major_2_requirement_keys(self, context):
        for major, reqs in context.major_2_requirement.items():
            assert isinstance(reqs, dict)


class TestGetters:
    @pytest.fixture(scope="class")
    def context(self):
        return load_all_data()

    def test_get_course_info_all(self, context):
        info = get_course_info(context)
        assert isinstance(info, dict)
        assert len(info) > 0

    def test_get_course_info_by_id(self, context):
        ids = get_course_info(context, "id")
        assert isinstance(ids, list)
        assert len(ids) > 0

    def test_get_course_info_specific(self, context):
        ids = get_course_info(context, "id")
        result = get_course_info(context, ids[0])
        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_course_info_missing_raises(self, context):
        with pytest.raises(InfoMissingError):
            get_course_info(context, "ZZZ9999")

    def test_get_course_id_list(self, context):
        ids = get_course_id_list(context)
        assert len(ids) == len(context.course_info)

    def test_get_course_list_all(self, context):
        cl = get_course_list(context)
        assert "Interdisciplinary Data Analytics" in cl

    def test_get_course_list_specific(self, context):
        cl = get_course_list(context, "Interdisciplinary Data Analytics")
        assert isinstance(cl, dict)

    def test_get_course_list_missing_raises(self, context):
        with pytest.raises(InfoMissingError):
            get_course_list(context, "NonexistentMajor")

    def test_get_equivalence_courses_all(self, context):
        eq = get_equivalence_courses(context)
        assert isinstance(eq, dict)

    def test_get_equivalence_courses_specific(self, context):
        eq = get_equivalence_courses(context, "Computer Science and Engineering")
        assert isinstance(eq, dict)
        for hk, sz in eq.items():
            assert determine_campus(hk) == "hk"
            assert determine_campus(sz) == "sz"

    def test_get_major_2_requirement(self, context):
        major = list(context.major_2_requirement.keys())[0]
        cats = context.major_2_requirement[major]
        category = list(cats.keys())[0]
        credits = get_major_2_requirement(context, major, category)
        assert isinstance(credits, int)
        assert credits >= 0


class TestConvertCourseId:
    @pytest.fixture(scope="class")
    def context(self):
        return load_all_data()

    def test_hk_to_sz(self, context):
        for major, mapping in context.equivalence_courses.items():
            if mapping:
                hk_code = list(mapping.keys())[0]
                sz_code = mapping[hk_code]
                assert convert_course_id(context, major, hk_code) == sz_code
                return

    def test_sz_to_hk(self, context):
        for major, mapping in context.equivalence_courses.items():
            if mapping:
                hk_code = list(mapping.keys())[0]
                sz_code = mapping[hk_code]
                assert convert_course_id(context, major, sz_code) == hk_code
                return

    def test_unknown_course_raises(self, context):
        major = list(context.equivalence_courses.keys())[0]
        with pytest.raises(InfoMissingError):
            convert_course_id(context, major, "ZZZ9999")


class TestCourseKey:
    """_course_key: canonical DB identity for a course (要求①)."""

    @pytest.fixture(scope="class")
    def context(self):
        return load_all_data()

    def test_hk_course_is_self(self, context):
        # A HK course id is its own canonical key.
        assert _course_key(context, "Interdisciplinary Data Analytics", "DOTE1030") == "DOTE1030"

    def test_sz_with_hk_equivalent_collapses_to_hk(self, context):
        # ECO2011 (SZ) <-> DOTE1030 (HK): same course must share one key.
        assert _course_key(context, "Interdisciplinary Data Analytics", "ECO2011") == "DOTE1030"

    def test_sz_without_equivalent_keeps_own_id(self, context):
        # A SZ course with no HK equivalent keeps its own id — never "Unavailable".
        major = "Interdisciplinary Data Analytics"
        sz_known = set(get_equivalence_courses(context, major).values())
        sz_no_equiv = next(
            c for c in get_course_id_list(context)
            if determine_campus(c) == "sz" and c not in sz_known
        )
        key = _course_key(context, major, sz_no_equiv)
        assert key == sz_no_equiv
        assert key != "Unavailable"

    def test_equivalent_pair_shares_key(self, context):
        # 要求①: a HK course and its SZ equivalent produce the same key.
        major = "Interdisciplinary Data Analytics"
        equiv = get_equivalence_courses(context, major)
        hk = next(iter(equiv))
        sz = equiv[hk]
        assert _course_key(context, major, hk) == _course_key(context, major, sz)


class TestStudyPeriodRead:
    """show_course_info('study_period'): read-side of the persistence loop."""

    @pytest.fixture(scope="class")
    def context(self):
        return load_all_data()

    @pytest.fixture
    def course_list(self, context):
        return get_course_list(context, "University Core")["Required Courses"]

    def test_guest_returns_blanks(self, context, course_list):
        # No user_id in session_state → all blanks, length matches course_list.
        out = show_course_info(context, "University Core", course_list, "hk", "study_period")
        assert out == ["" for _ in course_list]
        assert len(out) == len(course_list)

    def test_logged_in_empty_db_returns_blanks(self, context, course_list):
        # Logged-in user but no saved rows → all blanks, no InfoMissingError.
        st.session_state["user_id"] = "test-user"
        out = show_course_info(context, "University Core", course_list, "hk", "study_period")
        assert out == ["" for _ in course_list]

    def test_read_is_campus_agnostic(self, context, course_list):
        # 要求① read-side: key is _course_key, so campus arg no longer affects
        # the lookup — passing 'hk' or 'sz' yields the same result.
        st.session_state["user_id"] = "test-user"
        a = show_course_info(context, "University Core", course_list, "hk", "study_period")
        b = show_course_info(context, "University Core", course_list, "sz", "study_period")
        assert a == b


class TestDataOnChange:
    """data_on_change: write-side identity comes from the DataFrame index label."""

    def test_guest_skips_write(self, monkeypatch):
        import src.storage as storage
        df = pd.DataFrame(
            {"CUHK": ["DOTE1030 x"], "CUHKSZ": ["ECO2011 y"], "Credits": [3], "Study Period": ["Y1S1"]},
            index=["DOTE1030"],
        )
        upserts: list[dict] = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append(d))
        # no user_id set → early return, no upsert
        storage.data_on_change("anykey", df)
        assert upserts == []

    def test_rangeindex_guard_fires(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        df = pd.DataFrame(
            {"CUHK": ["DOTE1030 x"], "CUHKSZ": ["ECO2011 y"], "Credits": [3], "Study Period": ["Y1S1"]}
        )  # default RangeIndex — must be rejected
        errors: list[str] = []
        monkeypatch.setattr(st, "error", lambda *a, **k: errors.append(a[0] if a else ""))
        upserts: list[dict] = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append(d))
        storage.data_on_change("badkey", df)
        assert errors and "course keys" in errors[0]
        assert upserts == []  # guard returns before any write

    def test_edit_uses_index_label_as_course_id(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["goodkey"] = {
            "edited_rows": {"0": {"Study Period": "Year 2 Sem 1"}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": ["DOTE1030 Eco"], "CUHKSZ": ["ECO2011 Micro"], "Credits": [3], "Study Period": ["Year 1 Sem 1"]},
            index=["DOTE1030"],
        )
        upserts: list[dict] = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append(d))
        monkeypatch.setattr(storage, "delete_data", lambda *a, **k: None)
        storage.data_on_change("goodkey", df)
        assert len(upserts) == 1
        assert upserts[0]["course_id"] == "DOTE1030"        # index label, NOT "DOTE1030 Eco"
        assert upserts[0]["study_period"] == "Year 2 Sem 1"
        assert upserts[0]["id"] == "test-user"

    def test_delete_uses_index_label(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["delkey"] = {
            "edited_rows": {},
            "added_rows": [],
            "deleted_rows": [0],
        }
        df = pd.DataFrame(
            {"CUHK": ["DOTE1030 Eco"], "CUHKSZ": ["ECO2011 Micro"], "Credits": [3], "Study Period": ["Year 1 Sem 1"]},
            index=["DOTE1030"],
        )
        deletes: list[str] = []
        monkeypatch.setattr(storage, "delete_data", lambda uid, cid, **k: deletes.append(cid))
        storage.data_on_change("delkey", df)
        assert deletes == ["DOTE1030"]  # index label, not the display label


class TestUserInputOnChange:
    """user_input_on_change + per-section wrappers: identity = typed CUHK cell,
    routed to a section-specific DB table."""

    def test_guest_skips_write(self, monkeypatch):
        import src.storage as storage
        df = pd.DataFrame(
            {"CUHK": ["PHED1001"], "CUHKSZ": [""], "Credits": [1], "Study Period": ["Y1S1"]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.pe_on_change("anykey", df)  # no user_id
        assert upserts == []

    def test_pe_stores_typed_code_in_pe_table(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["pekey"] = {
            "edited_rows": {"0": {"CUHK": "PHED1001", "Study Period": "Year 1 Sem 1"}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [1], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.pe_on_change("pekey", df)
        assert len(upserts) == 1
        data, tbl = upserts[0]
        assert data["course_id"] == "PHED1001"          # typed code, not an index label
        assert data["study_period"] == "Year 1 Sem 1"
        assert data["credits"] == 1                     # user-typed credits persisted
        assert data["id"] == "test-user"
        assert tbl == "pe"                              # routed to the PE table

    def test_edited_credits_change_persisted(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["pekey3"] = {
            "edited_rows": {"0": {"Credits": 2}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": ["PHED1001"], "CUHKSZ": [""], "Credits": [1], "Study Period": ["Y1S1"]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.pe_on_change("pekey3", df)
        assert upserts[0][0]["credits"] == 2            # changed cell wins over base

    def test_empty_course_id_skipped(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["pekey2"] = {
            "edited_rows": {"0": {"Study Period": "Year 1 Sem 1"}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [1], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.pe_on_change("pekey2", df)
        assert upserts == []  # no course code typed yet → nothing to store


class TestUserInputRouting:
    """Each wrapper writes to its own table so sections never collide."""

    def test_college_ge_routes_to_own_table(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["gekey"] = {
            "edited_rows": {"0": {"CUHK": "UGCP1001", "Study Period": "Year 1 Sem 1"}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [3], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.college_ge_on_change("gekey", df)
        assert upserts[0][0]["course_id"] == "UGCP1001"
        assert upserts[0][1] == "college_ge"

    def test_four_area_routes_to_own_table(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["fakey"] = {
            "edited_rows": {"0": {"CUHK": "UGFN1001", "Study Period": "Year 2 Sem 1"}},
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [3], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.four_area_on_change("fakey", df)
        assert upserts[0][0]["course_id"] == "UGFN1001"
        assert upserts[0][1] == "four_area_ge"


class TestUserInputDynamic:
    """user_input_on_change handles added/deleted rows (num_rows='dynamic')."""

    def test_added_row_is_upserted(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["addkey"] = {
            "edited_rows": {},
            "added_rows": [{"CUHK": "UGCP2002", "CUHKSZ": "", "Credits": 3, "Study Period": "Year 2 Sem 2"}],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": ["", ""], "CUHKSZ": ["", ""], "Credits": [3, 3], "Study Period": ["", ""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.college_ge_on_change("addkey", df)
        assert len(upserts) == 1
        assert upserts[0][0]["course_id"] == "UGCP2002"
        assert upserts[0][0]["credits"] == 3            # added-row credits persisted
        assert upserts[0][0]["study_period"] == "Year 2 Sem 2"

    def test_added_row_without_course_id_skipped(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["addkey2"] = {
            "edited_rows": {},
            "added_rows": [{"CUHK": "", "Study Period": "Year 2 Sem 2"}],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [3], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.college_ge_on_change("addkey2", df)
        assert upserts == []

    def test_deleted_row_removed_by_typed_code(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["delkey"] = {
            "edited_rows": {},
            "added_rows": [],
            "deleted_rows": [1],
        }
        df = pd.DataFrame(
            {"CUHK": ["UGCP1001", "UGCP2002"], "CUHKSZ": ["", ""], "Credits": [3, 3], "Study Period": ["Y1S1", "Y2S2"]},
        )
        deletes: list = []
        monkeypatch.setattr(storage, "delete_data", lambda uid, cid, **k: deletes.append((cid, k.get("table_name"))))
        storage.college_ge_on_change("delkey", df)
        assert deletes == [("UGCP2002", "college_ge")]  # row 1's CUHK cell, own table


class TestUserInputPartialSave:
    """Any cell edit persists; empty study_period stored as None, one row's
    failure never blocks the others."""

    def test_empty_period_saved_as_none(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["fapart"] = {
            "edited_rows": {"0": {"CUHK": "UGFN1001"}},  # code typed, no period yet
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": [""], "CUHKSZ": [""], "Credits": [3], "Study Period": [""]},
        )
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", lambda uid, d, **k: upserts.append((d, k.get("table_name"))))
        storage.four_area_on_change("fapart", df)
        assert len(upserts) == 1
        data, tbl = upserts[0]
        assert data["course_id"] == "UGFN1001"
        assert data["study_period"] is None   # empty → NULL passes DB CHECK
        assert data["credits"] == 3           # default credits from the table
        assert tbl == "four_area_ge"

    def test_row_failure_does_not_block_others(self, monkeypatch):
        import src.storage as storage
        st.session_state["user_id"] = "test-user"
        st.session_state["fabatch"] = {
            "edited_rows": {
                "0": {"CUHK": "UGFN1001", "Study Period": "Year 1 Sem 1"},
                "1": {"CUHK": "UGGA1001", "Study Period": "Year 2 Sem 1"},
            },
            "added_rows": [],
            "deleted_rows": [],
        }
        df = pd.DataFrame(
            {"CUHK": ["", ""], "CUHKSZ": ["", ""], "Credits": [3, 3], "Study Period": ["", ""]},
        )

        calls = {"n": 0}
        def flaky_upsert(uid, d, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated DB failure")  # first row fails
            upserts.append((d, k.get("table_name")))
        upserts: list = []
        monkeypatch.setattr(storage, "upsert_data", flaky_upsert)
        errors: list = []
        monkeypatch.setattr("streamlit.error", lambda *a, **k: errors.append(a[0] if a else ""))
        storage.four_area_on_change("fabatch", df)
        assert len(upserts) == 1                     # second row still saved
        assert upserts[0][0]["course_id"] == "UGGA1001"
        assert errors and "UGFN1001" in errors[0]    # failure surfaced for row 1
