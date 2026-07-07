import pytest
from src.data_retrieval import (
    load_all_data,
    determine_campus,
    convert_course_id,
    get_equivalence_courses,
    get_course_info,
    get_course_list,
    get_course_id_list,
    get_major_2_requirement,
    CourseDataContext,
    DataLoadError,
    FileMissingError,
    DataFormatError,
    InfoMissingError,
)


# ---------- setup ----------

@pytest.fixture(scope="module")
def ctx():
    return load_all_data()


# ---------- determine_campus ----------

def test_determine_campus_hk():
    assert determine_campus("CSCI1001") == "hk"  # 4th char 'I' → alpha

def test_determine_campus_sz():
    assert determine_campus("CSC1001") == "sz"   # 4th char '1' → digit

def test_determine_campus_too_short():
    with pytest.raises(DataLoadError):
        determine_campus("ABC")


# ---------- load_all_data ----------

def test_load_all_data_returns_context(ctx):
    assert isinstance(ctx, CourseDataContext)

def test_course_info_not_empty(ctx):
    assert len(ctx.course_info) > 0

def test_equivalence_courses_not_empty(ctx):
    assert len(ctx.equivalence_courses) > 0

def test_equivalence_bidicts_match(ctx):
    for major, mapping in ctx.equivalence_courses.items():
        b = ctx.equivalence_bidicts[major]
        assert len(b) == len(mapping)
        for hk, sz in mapping.items():
            assert b[hk] == sz
            assert b.inverse[sz] == hk

def test_course_list_not_empty(ctx):
    assert len(ctx.course_list) > 0

def test_major_2_requirement_not_empty(ctx):
    assert len(ctx.major_2_requirement) > 0

@pytest.mark.parametrize("file_arg", ["data/course_list.csv", "data/equivalence_courses.csv", "data/course_list.json", "data/2nd_major_credit_requirement.json"])
def test_data_files_exist(file_arg):
    """Sanity: all required data files exist on disk."""
    import os
    assert os.path.isfile(file_arg), f"Missing: {file_arg}"


# ---------- convert_course_id ----------

MAJOR = "Computer Science and Engineering"

def test_convert_hk_to_sz(ctx):
    hk_course = next(iter(ctx.equivalence_bidicts[MAJOR]))
    sz_course = convert_course_id(ctx, MAJOR, hk_course)
    assert sz_course != hk_course
    assert sz_course == ctx.equivalence_bidicts[MAJOR][hk_course]

def test_convert_sz_to_hk(ctx):
    sz_course = next(iter(ctx.equivalence_bidicts[MAJOR].values()))
    hk_course = convert_course_id(ctx, MAJOR, sz_course)
    assert hk_course != sz_course
    assert ctx.equivalence_bidicts[MAJOR][hk_course] == sz_course

def test_convert_missing_course(ctx):
    with pytest.raises(InfoMissingError):
        convert_course_id(ctx, MAJOR, "ZZZ9999")


# ---------- get_equivalence_courses ----------

def test_get_equivalence_all(ctx):
    result = get_equivalence_courses(ctx, "all")
    assert isinstance(result, dict)
    assert MAJOR in result

def test_get_equivalence_single_major(ctx):
    result = get_equivalence_courses(ctx, MAJOR)
    assert isinstance(result, dict)
    assert len(result) > 0

def test_get_equivalence_missing_major(ctx):
    with pytest.raises(InfoMissingError):
        get_equivalence_courses(ctx, "NonExistentMajor")


# ---------- get_course_info ----------

def test_get_course_info_all(ctx):
    result = get_course_info(ctx, "all")
    assert isinstance(result, dict)

def test_get_course_info_id_list(ctx):
    result = get_course_info(ctx, "id")
    assert isinstance(result, list)

def test_get_course_info_single(ctx):
    cid = next(iter(ctx.course_info))
    result = get_course_info(ctx, cid)
    assert isinstance(result, list)
    assert len(result) == 2  # [title, units]

def test_get_course_info_missing(ctx):
    with pytest.raises(InfoMissingError):
        get_course_info(ctx, "ZZZ9999")


# ---------- get_course_list ----------

def test_get_course_list_all(ctx):
    result = get_course_list(ctx, "all")
    assert isinstance(result, dict)

def test_get_course_list_single_major(ctx):
    result = get_course_list(ctx, MAJOR)
    assert isinstance(result, dict)

def test_get_course_list_missing_major(ctx):
    with pytest.raises(InfoMissingError):
        get_course_list(ctx, "NonExistentMajor")


# ---------- get_course_id_list ----------

def test_get_course_id_list(ctx):
    ids = get_course_id_list(ctx)
    assert isinstance(ids, list)
    assert all(isinstance(x, str) for x in ids)
    assert len(ids) == len(ctx.course_info)


# ---------- get_major_2_requirement ----------

def test_get_major_2_requirement(ctx):
    # Pick first major that has requirements
    major = next(iter(ctx.major_2_requirement))
    cat = next(iter(ctx.major_2_requirement[major]))
    result = get_major_2_requirement(ctx, major, cat)
    assert isinstance(result, int)
