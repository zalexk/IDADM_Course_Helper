"""Tests for data_retrieval.py — pure functions and data integrity."""

import pytest
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
