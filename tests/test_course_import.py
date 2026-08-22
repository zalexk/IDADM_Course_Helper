"""Tests for src/course_import.py — offline pipeline: rendering, term
normalization, LLM-reply parsing, canonicalization, preview building, and
confirmed writes. Uses a fake OpenAI client and monkeypatched storage; no
network, no secrets.
"""

from types import SimpleNamespace

import base64
import io

import pandas as pd
import pytest
import streamlit as st
from PIL import Image

import src.course_import as ci
from src.data_retrieval import load_all_data
from src.course_import import (
    CourseImportError,
    build_preview_rows,
    canonical_course_id,
    default_category,
    extract_courses,
    normalize_period,
    parse_llm_json,
    render_pages,
    write_confirmed,
)


def _png_bytes(text : str = "CSCI1120", size : tuple[int, int] = (400, 200)) -> bytes:
    """Synthesize a small PNG with text drawn on it."""
    image = Image.new("RGB", size, color="white")
    from PIL import ImageDraw

    ImageDraw.Draw(image).text((10, 10), text, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletions:
    def __init__(self, content, recorder):
        self._content = content
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder.append(kwargs)
        class _R:
            choices = [_FakeChoice(self._content)]
        return _R()


class FakeClient:
    """Duck-typed openai.OpenAI returning a canned completion."""

    def __init__(self, content : str):
        self.calls : list[dict] = []
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(content, self.calls),
        )

class TestNormalizePeriod:
    def test_exact_key(self):
        assert normalize_period("Year 3 Sem 1") == "Year 3 Sem 1"

    def test_semester_variant_and_case_whitespace(self):
        assert normalize_period("  year 3   semester 1 ") == "Year 3 Sem 1"

    def test_summer_ambiguous_is_empty(self):
        assert normalize_period("Year 1 Summer") == ""

    def test_summer_with_campus(self):
        assert normalize_period("Year 2 Summer (CUHKSZ)") == "Year 2 Summer (CUHKSZ)"
        assert normalize_period("year 1 summer (cuhk)") == "Year 1 Summer (CUHK)"

    def test_none_and_garbage(self):
        assert normalize_period(None) == ""
        assert normalize_period("") == ""
        assert normalize_period("whatever 2024") == ""


class TestParseLlmJson:
    def test_fenced_array(self):
        assert parse_llm_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]

    def test_array_in_prose(self):
        assert parse_llm_json('Sure! [{"x": 2}] hope this helps') == [{"x": 2}]

    def test_non_dict_rows_dropped(self):
        assert parse_llm_json('[["row"], {"ok": 1}]') == [{"ok": 1}]

    def test_no_array_raises(self):
        with pytest.raises(CourseImportError):
            parse_llm_json("no array here")

    def test_object_not_array_raises(self):
        with pytest.raises(CourseImportError):
            parse_llm_json('{"courses": []}')

    def test_invalid_json_raises(self):
        with pytest.raises(CourseImportError):
            parse_llm_json("[{broken]")


class TestCanonicalCourseId:
    context = load_all_data()

    def test_hk_passthrough_normalized(self):
        assert canonical_course_id(self.context, " csci1120 ") == "CSCI1120"

    def test_real_sz_to_hk(self):
        # Pick one real equivalence pair out of the catalogue data.
        pair = next(
            (hk, sz)
            for mapping in self.context.equivalence_courses.values()
            for hk, sz in mapping.items()
        )
        hk_id, sz_id = pair
        result = canonical_course_id(self.context, sz_id.lower())
        assert result == str(hk_id).upper()
        assert result != sz_id.upper()

    def test_unknown_sz_unchanged(self):
        assert canonical_course_id(self.context, "ZZZZ0000") == "ZZZZ0000"

    def test_empty_code(self):
        assert canonical_course_id(self.context, "") == ""


class TestRenderPages:
    def test_png_roundtrip(self):
        pages = render_pages(_png_bytes(), "shot.png")
        assert len(pages) == 1
        decoded = Image.open(io.BytesIO(pages[0]))
        assert decoded.format == "PNG"

    def test_jpg_extension_accepted(self):
        image = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        pages = render_pages(buffer.getvalue(), "shot.jpeg")
        assert len(pages) == 1

    def test_txt_rejected(self):
        with pytest.raises(CourseImportError):
            render_pages(b"not an image", "notes.txt")

    def test_bad_bitmap_bytes_rejected(self):
        with pytest.raises(CourseImportError):
            render_pages(b"\x89PNG garbage", "fake.png")


class TestExtractCourses:
    CANNED = '[{"code": "CSCI1120", "title": "Introduction to Computing", ' \
             '"term": "Year 1 Sem 1", "credits": 3}]'

    def test_parses_canned_completion(self):
        client = FakeClient(self.CANNED)
        rows = extract_courses(client, [_png_bytes()], model="test-model")
        assert rows[0]["code"] == "CSCI1120"
        assert len(rows) == 1

    def test_sends_images_as_data_urls(self):
        client = FakeClient(self.CANNED)
        png = _png_bytes()
        extract_courses(client, [png, png], model="m")
        request = client.calls[0]
        content = request["messages"][1]["content"]
        images = [part for part in content if part["type"] == "image_url"]
        assert len(images) == 2
        expected_prefix = "data:image/png;base64,"
        assert all(part["image_url"]["url"].startswith(expected_prefix) for part in images)
        # Round-trip the first payload back to identical bytes.
        b64 = images[0]["image_url"]["url"][len(expected_prefix):]
        assert base64.b64decode(b64) == png

    def test_network_error_wraps(self):
        class _Boom:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        raise ConnectionError("boom")
        with pytest.raises(CourseImportError):
            extract_courses(_Boom(), [_png_bytes()], model="m")

    def test_missing_key_raises_before_client_use(self, monkeypatch):
        monkeypatch.setattr(st, "secrets", {}, raising=False)
        with pytest.raises(CourseImportError, match="LLM_API_KEY"):
            ci._llm_config()


class TestBuildPreviewRows:
    context = load_all_data()
    MAJOR_2 = "Computer Science and Engineering"

    ROWS = [
        {"code": "CSCI1120", "title": "Intro", "term": "Year 1 Sem 1"},
        {"code": "GFH1000", "title": "In Heritage", "term": "year 2 semester 2"},
        {"code": "ZZZZ9999", "title": "Ghost Course", "term": "Nowhere"},
        {"code": "", "title": "blank code dropped"},
        {"code": "csci1110", "title": "duplicate of first"},
    ]

    def test_columns_and_recognition(self):
        df = build_preview_rows(self.context, self.ROWS, [], self.MAJOR_2)
        assert list(df.columns) == [
            "Course ID", "Course", "Recognized",
            "Existing Period", "Study Period", "Credits", "Category",
        ]
        first = df.iloc[0]
        assert first["Course ID"] == "CSCI1120"
        assert bool(first["Recognized"]) is True
        assert first["Course"] == f"CSCI1120 {self.context.course_info['CSCI1120'][0]}"

    def test_credits_catalogue_vs_transcript(self):
        # Recognized -> catalogue credits; unrecognized -> JSON credits.
        rows = [
            {"code": "CSCI1120", "title": "Intro", "term": "Year 1 Sem 1"},
            {"code": "PED1201", "title": "Badminton", "term": "Year 1 Sem 2",
             "credits": 1},
            {"code": "ZZZZ9999", "title": "Ghost", "term": "Year 1 Sem 1"},
        ]
        df = build_preview_rows(self.context, rows, [], self.MAJOR_2)
        assert df.iloc[0]["Credits"] == int(self.context.course_info["CSCI1120"][1])
        assert df.iloc[1]["Credits"] == 1   # transcript credits kept
        assert pd.isna(df.iloc[2]["Credits"]) # no credits in JSON -> empty

    def test_existing_period_lookup_and_duplicates(self):
        existing = [{"course_id": "CSCI1120", "study_period": "Year 4 Sem 2"}]
        df = build_preview_rows(self.context, self.ROWS, existing, self.MAJOR_2)
        row = df[df["Course ID"] == "CSCI1120"].iloc[0]
        assert row["Existing Period"] == "Year 4 Sem 2"
        # Duplicate lowercase id collapsed into one row.
        assert (df["Course ID"] == "CSCI1120").sum() == 1

    def test_existing_period_spans_all_tables(self):
        # fetch_all_planned rows: same course in two tables -> first
        # non-empty period wins, regardless of the source table.
        existing = [
            {"course_id": "PHED1000", "study_period": None, "source": "study_plan"},
            {"course_id": "PHED1000", "study_period": "Year 1 Sem 1", "source": "pe"},
        ]
        df = build_preview_rows(
            self.context,
            [{"code": "PHED1000", "title": "PE", "term": ""}],
            existing,
            self.MAJOR_2,
        )
        assert df.iloc[0]["Existing Period"] == "Year 1 Sem 1"
        assert df.iloc[0]["Category"] == "University Core: PE"

    def test_unrecognized_flagged_and_term_blank(self):
        df = build_preview_rows(self.context, self.ROWS, [], self.MAJOR_2)
        ghost = df[df["Course ID"] == "ZZZZ9999"].iloc[0]
        assert bool(ghost["Recognized"]) is False
        assert str(ghost["Course"]).startswith("⚠ ")
        assert ghost["Study Period"] == ""  # unmatched term -> ''

    def test_equivalence_reverse_maps_sz_code(self):
        pair = next(
            (hk, sz)
            for mapping in self.context.equivalence_courses.values()
            for hk, sz in mapping.items()
        )
        hk_id, sz_id = pair
        df = build_preview_rows(
            self.context,
            [{"code": sz_id, "title": "x", "term": "Year 1 Sem 1"}],
            [],
            self.MAJOR_2,
        )
        assert df.iloc[0]["Course ID"] == str(hk_id).upper()


class TestDefaultCategory:
    context = load_all_data()
    MAJOR_2 = "Computer Science and Engineering"

    @pytest.mark.parametrize("cid,expected", [
        ("PHED1000", "University Core: PE"),
        ("CSC3050", "IDA: Elective Group A"),   # also a 2nd-major required course
        ("ECO3121", "IDA: Elective Group B"),
        ("CSCI1120", "2nd Major: Required Courses"),  # HK form of CSC3002
        ("SEEM4998", "2nd Major: Research Component"),
        ("CSCI1530", "2nd Major: Elective"),
        ("CSCI1130", "Other Courses"),          # catalogue, no section here
        ("GECC1130", "University Core: College GE"),   # must not be caught by GEC
        ("GECW1000", "University Core: College GE"),   # must not be caught by GEC
        ("GENA1000", "University Core: College GE"),
        ("GEUC2000", "University Core: College GE"),
        ("GEC1001", "University Core: Four Areas of GE"),  # SZ prefix still wins
        ("PED1201", "University Core: PE"),
        ("ZZZZ9999", "Other Courses"),          # unknown id
    ])
    def test_classification(self, cid, expected):
        assert default_category(self.context, cid, self.MAJOR_2) == expected


class TestWriteConfirmed:
    context = load_all_data()

    def _capture(self, monkeypatch):
        calls : list[tuple] = []
        monkeypatch.setattr(
            ci, "upsert_data",
            lambda user_id, data, table_name="study_plan":
                calls.append((table_name, data)) or ([],),
        )
        return calls

    def test_category_routes_to_tables(self, monkeypatch):
        calls = self._capture(monkeypatch)
        df = pd.DataFrame([
            {"Course ID": "PHED1000", "Course": "⚠ PE Course", "Recognized": False,
             "Study Period": "Year 1 Sem 1", "Credits": 1,
             "Category": "University Core: PE"},
            {"Course ID": "GEB2000", "Course": "⚠ Area B", "Recognized": False,
             "Study Period": "", "Credits": 3,
             "Category": "University Core: Four Areas of GE"},
            {"Course ID": "ELTU1001", "Course": "⚠ English", "Recognized": False,
             "Study Period": "Year 1 Sem 2", "Credits": None,
             "Category": "University Core: English Language"},
            {"Course ID": "CHLT1001", "Course": "CHLT1001 Chinese", "Recognized": False,
             "Study Period": "Year 1 Sem 1", "Credits": None,
             "Category": "University Core: Chinese Language"},
        ])
        count = ci.write_confirmed(self.context, "u", df)
        assert count == 4
        by_id = {d["course_id"]: (t, d) for t, d in calls}
        # Input tables store 'CODE Title' + credits; english/study_plan the
        # bare code with no credits.
        assert by_id["PHED1000 PE Course"] == (
            "pe", {"id": "u", "course_id": "PHED1000 PE Course",
                   "credits": 1, "study_period": "Year 1 Sem 1"},
        )
        assert by_id["GEB2000 Area B"][0] == "four_area_ge"
        assert by_id["GEB2000 Area B"][1]["credits"] == 3
        assert by_id["ELTU1001"] == (
            "english", {"id": "u", "course_id": "ELTU1001",
                        "study_period": "Year 1 Sem 2"},
        )
        assert by_id["CHLT1001"][0] == "study_plan"
        assert "credits" not in by_id["CHLT1001"][1]

    def test_input_table_identity_and_credit_defaults(self, monkeypatch):
        calls = self._capture(monkeypatch)
        df = pd.DataFrame([
            {"Course ID": "PED1201", "Course": "⚠ Badminton", "Recognized": False,
             "Study Period": "Year 1 Sem 2", "Credits": 1,
             "Category": "University Core: PE"},
            {"Course ID": "GECC1130", "Course": "⚠ College GE", "Recognized": False,
             "Study Period": "Year 2 Sem 1", "Credits": None,
             "Category": "University Core: College GE"},
        ])
        assert ci.write_confirmed(self.context, "u", df) == 2
        ped = calls[0]
        assert ped[0] == "pe"
        assert ped[1]["course_id"] == "PED1201 Badminton"  # id + name merged
        assert ped[1]["credits"] == 1
        college = calls[1]
        assert college[0] == "college_ge"
        assert college[1]["course_id"] == "GECC1130 College GE"
        assert college[1]["credits"] == 3  # missing credits -> tab default

    def test_preview_roundtrip_ped_example(self, monkeypatch):
        # The user's example: PED1201 Badminton lands in pe as
        # 'PED1201 Badminton' with the transcript's credits.
        calls = self._capture(monkeypatch)
        preview = build_preview_rows(
            self.context,
            [{"code": "PED1201", "title": "Badminton",
              "term": "Year 1 Sem 2", "credits": 1}],
            [],
            "Computer Science and Engineering",
        )
        assert ci.write_confirmed(self.context, "u", preview) == 1
        assert calls[0] == ("pe", {
            "id": "u", "course_id": "PED1201 Badminton",
            "credits": 1, "study_period": "Year 1 Sem 2",
        })

    def test_study_plan_category_requires_catalogue(self, monkeypatch):
        calls = self._capture(monkeypatch)
        df = pd.DataFrame([
            {"Course ID": "CSCI1120", "Recognized": True, "Study Period": "Year 1 Sem 1",
             "Category": "IDA: Elective Group A"},
            {"Course ID": "MATH1010", "Recognized": True, "Study Period": "",
             "Category": "Other Courses"},
            {"Course ID": "ZZZZ9999", "Recognized": True, "Study Period": "Year 1 Sem 1",
             "Category": "IDA: Elective Group A"},
        ])
        count = ci.write_confirmed(self.context, "user-1", df)
        assert count == 2                      # unknown id skipped...
        assert calls[0] == ("study_plan", {
            "id": "user-1", "course_id": "CSCI1120", "study_period": "Year 1 Sem 1",
        })
        assert calls[1][1]["study_period"] is None  # empty period -> NULL
        assert {d["course_id"] for _, d in calls} == {"CSCI1120", "MATH1010"}

    def test_input_category_imports_unrecognized_id(self, monkeypatch):
        # A real course outside the catalogue: an explicit input-table
        # category is the user saying where it belongs, so it imports.
        calls = self._capture(monkeypatch)
        df = pd.DataFrame([
            {"Course ID": "XXXX9999", "Recognized": False, "Study Period": "Year 2 Sem 1",
             "Category": "University Core: College GE"},
        ])
        assert ci.write_confirmed(self.context, "u", df) == 1
        assert calls[0][0] == "college_ge"

    def test_missing_category_falls_back_to_prefix_and_catalogue(self, monkeypatch):
        # Stale preview without a Category column (pre-migration session
        # state): routing degrades to prefix + catalogue matching.
        calls = self._capture(monkeypatch)
        df = pd.DataFrame([
            {"Course ID": "PHED1000", "Recognized": False, "Study Period": "Year 1 Sem 1"},
            {"Course ID": "PED2000", "Recognized": False, "Study Period": ""},
            {"Course ID": "UGDA1234", "Recognized": False, "Study Period": "Year 2 Sem 2"},
            {"Course ID": "GEB2000", "Recognized": False, "Study Period": ""},
            {"Course ID": "CHLT1001", "Recognized": False, "Study Period": "Year 1 Sem 1"},
            {"Course ID": "ELTU1001", "Recognized": False, "Study Period": "Year 1 Sem 2"},
            {"Course ID": "ENG2050", "Recognized": False, "Study Period": ""},
            {"Course ID": "ZZZZ9999", "Recognized": True, "Study Period": "Year 1 Sem 1"},
        ])
        count = ci.write_confirmed(self.context, "u", df)
        assert count == 7  # unknown id without a category is the only skip
        by_id = {d["course_id"]: t for t, d in calls}
        assert by_id["PHED1000"] == "pe"
        assert by_id["PED2000"] == "pe"
        assert by_id["UGDA1234"] == "four_area_ge"
        assert by_id["GEB2000"] == "four_area_ge"
        assert by_id["CHLT1001"] == "study_plan"
        assert by_id["ELTU1001"] == "english"
        assert by_id["ENG2050"] == "english"
        assert "ZZZZ9999" not in by_id

    def test_row_failure_keeps_others(self, monkeypatch):
        seen : list[str] = []

        def flaky(user_id, data, table_name="study_plan"):
            seen.append(data["course_id"])
            if data["course_id"] == "PHED2":
                raise RuntimeError("supabase down")

        monkeypatch.setattr(ci, "upsert_data", flaky)
        df = pd.DataFrame([
            {"Course ID": "CSCI1120", "Recognized": True, "Study Period": ""},
            {"Course ID": "PHED2", "Recognized": True, "Study Period": ""},
            {"Course ID": "MATH1010", "Recognized": True, "Study Period": ""},
        ])
        count = ci.write_confirmed(self.context, "u", df)
        assert seen == ["CSCI1120", "PHED2", "MATH1010"]  # continued past the failure
        assert count == 2                                  # failed row not counted


class TestConfigGuards:
    def test_missing_llm_key_message(self, monkeypatch):
        monkeypatch.setattr(st, "secrets", {"OTHER": 1}, raising=False)
        with pytest.raises(CourseImportError, match="LLM_API_KEY missing"):
            ci._llm_config()

    def test_optional_overrides(self, monkeypatch):
        monkeypatch.setattr(st, "secrets", {
            "LLM_API_KEY": "sk-x",
            "COURSE_IMPORT_MODEL": "my-vision-model",
            "LLM_BASE_URL": "https://api.example.com/v1",
        }, raising=False)

        api_key, base_url, model = ci._llm_config()
        assert api_key == "sk-x"
        assert base_url == "https://api.example.com/v1"
        assert model == "my-vision-model"

    def test_default_model_without_optional_keys(self, monkeypatch):
        monkeypatch.setattr(st, "secrets", {"LLM_API_KEY": "sk-y"}, raising=False)
        _, base_url, model = ci._llm_config()
        assert base_url is None
        assert model == ci.DEFAULT_MODEL
