"""Course import: batch-load previously-taken courses from a transcript
image/PDF into the study plan.

Pipeline (each arrow is an offline-testable seam):

    file bytes --render_pages--> PNG page images
               --extract_courses (OpenAI-compatible vision LLM)--> raw rows
               --build_preview_rows--> preview DataFrame (user fixes terms)
               --write_confirmed--> existing Supabase `study_plan` table

Config is read lazily from st.secrets at call time (never at import), so a
missing OPENAI_API_KEY surfaces as one caught CourseImportError in the UI
instead of crashing the process - unlike src/storage.py's import-time init.
"""

import base64
import io
import json
from typing import Any

import pandas as pd
import pypdfium2 as pdfium
import streamlit as st
from PIL import Image

from app.constant import STUDY_CAMPUS
from src.data_retrieval import (
    CourseDataContext,
    DataLoadError,
    InfoMissingError,
    _course_key,
    determine_campus,
    get_course_info,
    get_course_list,
)
from src.storage import upsert_data
# Sections a user sees on the app's tabs -> import category. Categories map
# onto the underlying Supabase tables; the labels stay user-facing so the
# preview never exposes table names like "study_plan" or "pe".
_IDA : str = "Interdisciplinary Data Analytics"

CATEGORY_TABLES : dict[str, str] = {
    "University Core: PE": "pe",
    "University Core: College GE": "college_ge",
    "University Core: Four Areas of GE": "four_area_ge",
    "University Core: English Language": "english",
    "University Core: GE Courses": "study_plan",
    "University Core: Chinese Language": "study_plan",
    "IDA: Faculty Package": "study_plan",
    "IDA: Required Courses": "study_plan",
    "IDA: COOP": "study_plan",
    "IDA: Elective Group A": "study_plan",
    "IDA: Elective Group B": "study_plan",
    "2nd Major: Required Courses": "study_plan",
    "2nd Major: Research Component": "study_plan",
    "2nd Major: Elective": "study_plan",
    "Other Courses": "study_plan",
}

IMPORT_CATEGORIES : tuple[str, ...] = tuple(CATEGORY_TABLES)

# (category, major, section key) checked in order; first section containing
# the course wins. Electives and 2nd-major sections depend on the selected
# 2nd major and are appended at call time in default_category.
_SECTION_CATEGORY : tuple[tuple[str, str, str], ...] = (
    ("University Core: Chinese Language", "University Core", "Chinese Language"),
    ("University Core: GE Courses", "University Core", "Required Courses"),
    ("IDA: Faculty Package", _IDA, "Faculty Package"),
    ("IDA: Required Courses", _IDA, "Required Courses"),
    ("IDA: COOP", _IDA, "COOP"),
)

# Course-id prefixes that are routed to an input table also get that table's
# user-facing category.
_RULE_CATEGORY : dict[str, str] = {
    "pe": "University Core: PE",
    "college_ge": "University Core: College GE",
    "four_area_ge": "University Core: Four Areas of GE",
    "english": "University Core: English Language",
}


def _section_keys(context : CourseDataContext, major : str, section : str) -> set[str]:
    """Canonical keys of one catalogue section."""
    return {
        _course_key(context, major, c)
        for c in get_course_list(context, major)[section]
    }


def default_category(context : CourseDataContext, cid : str, major_2 : str) -> str:
    """User-facing category for a course id (see CATEGORY_TABLES).

    Prefix-matched non-catalogue courses get their input-table category;
    catalogue courses get the first section containing them (University Core
    before 1st major before 2nd major); anything else lands in the generic
    "Other Courses" bucket.
    """
    routed : tuple[str, str] | None = classify_course(cid)
    if routed is not None:
        return _RULE_CATEGORY[routed[1]]
    for category, major, section in _SECTION_CATEGORY:
        if cid in _section_keys(context, major, section):
            return category
    electives = get_course_list(context, major_2)["1st Major Elective Courses"]
    for category, group in (
        ("IDA: Elective Group A", "A"),
        ("IDA: Elective Group B", "B"),
    ):
        if cid in {_course_key(context, _IDA, c) for c in electives[group]}:
            return category
    for category, section in (
        ("2nd Major: Required Courses", "Required Courses"),
        ("2nd Major: Research Component", "Research Component"),
        ("2nd Major: Elective", "2nd Major Elective Courses"),
    ):
        if cid in _section_keys(context, major_2, section):
            return category
    return "Other Courses"



class CourseImportError(Exception):
    """Any course-import failure; the UI maps it to a single st.error."""


DEFAULT_MODEL : str = "gemini-3.5-flash-lite"
MAX_PAGES : int = 20           # PDF pages parsed per upload
MAX_IMAGE_EDGE : int = 1600    # px cap on the long edge (token cost control)
RENDER_SCALE : int = 2         # ~144 dpi PDF rasterization
SUPPORTED_TYPES : tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "pdf")
PREVIEW_COLUMNS : list[str] = [
    "Course ID", "Course", "Recognized", "Existing Period", "Study Period",
    "Credits", "Category",
]

# Campus-prefix rules for courses OUTSIDE the catalogue (user-input sections
# of University Core). Prefixes are matched case-insensitively on the course
# id, first match wins; catalogue courses never reach these rules.
#   CUHK: PHED* (PE), GE[CC|NA|SC|UC|MC|SH|CW|YS|WS]* (College GE),
#         UG[ABCD]* (Four Area GE), ELTU* (English)
#   CUHKSZ: PED* (PE), GE[ABCD]* (Four Area GE), ENG* (English)
_INPUT_PREFIX_RULES : tuple[tuple[str, str, str], ...] = (
    # (prefix, campus, destination table)
    # College GE prefixes must precede GEC: "GECC1130"/"GECW1000" also
    # start with "GEC", which is the CUHKSZ Four Area prefix.
    ("GECC", "CUHK", "college_ge"),
    ("GENA", "CUHK", "college_ge"),
    ("GESC", "CUHK", "college_ge"),
    ("GEUC", "CUHK", "college_ge"),
    ("GEMC", "CUHK", "college_ge"),
    ("GESH", "CUHK", "college_ge"),
    ("GECW", "CUHK", "college_ge"),
    ("GEYS", "CUHK", "college_ge"),
    ("GEWS", "CUHK", "college_ge"),
    ("PHED", "CUHK", "pe"),
    ("PED", "CUHKSZ", "pe"),
    ("UGA", "CUHK", "four_area_ge"),
    ("UGB", "CUHK", "four_area_ge"),
    ("UGC", "CUHK", "four_area_ge"),  # note: UGCP1001/2 are catalogue rows and
    ("UGD", "CUHK", "four_area_ge"),  # never reach this table via import
    ("GEA", "CUHKSZ", "four_area_ge"),
    ("GEB", "CUHKSZ", "four_area_ge"),
    ("GEC", "CUHKSZ", "four_area_ge"),
    ("GED", "CUHKSZ", "four_area_ge"),
    ("ELTU", "CUHK", "english"),
    ("ENG", "CUHKSZ", "english"),
)


def classify_course(cid : str) -> tuple[str, str] | None:
    """(campus, input-table) for prefix-matched non-catalogue courses;
    None when no rule applies (catalogue course or unknown prefix)."""
    upper = cid.strip().upper()
    for prefix, campus, table in _INPUT_PREFIX_RULES:
        if upper.startswith(prefix):
            return campus, table
    return None

_SYSTEM_PROMPT : str = """\
You are a precise academic-transcript parser. Extract EVERY course entry
visible in the attached document images, across all pages.
Output ONLY a JSON array - no prose, no markdown fences - where each element
has exactly these keys:
    {
      "code": <course code string or null>,
      "title": <course title string or null>,
      "term": <academic term string or null>,
      "credits": <credit units number or null>
    }
   
Rules:
- Copy course codes character-for-character; use null if unreadable.
- "term" examples: "Year 3 Sem 1", "2023-24 Term 2", "Year 1 Summer (CUHK)".
- Never invent courses that are not printed in the document.
- Omit the course with 0 credit
- Omit the space in the course ID, e.g. "ENGG 1110" should convert into "ENGG1110"

Notice:
- The admission year for the student is defaulted to be 2025/26, and "Term" is equivalent to "Sem". Hence, for 2025-26 Term 1, you should identify it as "Year 1 Sem 1" 
- For the course ID starting with "ZSZ-", should be identify it as course taken in CUHK(SZ) and remove "ZSZ-". For example, "ZSZ-DDA 2001" should convert into "DDA2001"image 
"""


# --- configuration & client -------------------------------------------------

def _llm_config() -> tuple[str, str | None, str]:
    """(api_key, base_url, model), read lazily at call time."""
    try:
        api_key : str = st.secrets["LLM_API_KEY"]
    except (KeyError, FileNotFoundError):
        raise CourseImportError(
            "LLM_API_KEY missing in .streamlit/secrets.toml"
        ) from None
    base_url : str | None = st.secrets.get("LLM_BASE_URL")
    model : str = st.secrets.get("COURSE_IMPORT_MODEL") or DEFAULT_MODEL
    return api_key, base_url, model

@st.cache_resource
def _get_client(cfg : tuple[str, str | None, str]) -> Any:
    """OpenAI-compatible client, cached per (api_key, base_url)."""
    from openai import OpenAI

    api_key, base_url, _model = cfg
    return OpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=2)


# --- pure helpers (offline unit-testable) -----------------------------------

def _encode_png(image : Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _render_bitmap(file_bytes : bytes) -> bytes:
    """Decode a screenshot, cap its resolution, return PNG bytes."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception as e:
        raise CourseImportError(f"Cannot decode image: {e}") from e
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
    return _encode_png(image)


def _render_pdf(file_bytes : bytes) -> list[bytes]:
    try:
        document = pdfium.PdfDocument(file_bytes)
    except Exception as e:
        raise CourseImportError(f"Cannot open PDF: {e}") from e
    pages : list[bytes] = []
    try:
        for index in range(min(len(document), MAX_PAGES)):
            bitmap = document[index].render(scale=RENDER_SCALE)
            pages.append(_encode_png(bitmap.to_pil()))
    except Exception as e:
        raise CourseImportError(f"PDF page rendering failed: {e}") from e
    return pages


def render_pages(file_bytes : bytes, filename : str) -> list[bytes]:
    """Transcript file bytes -> PNG page images (PDFs capped at MAX_PAGES;
    truncation is surfaced by the caller)."""
    lowered = filename.casefold()
    if lowered.endswith(".pdf"):
        return _render_pdf(file_bytes)
    if lowered.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return [_render_bitmap(file_bytes)]
    raise CourseImportError(
        f"Unsupported course-import file type: {filename} "
        f"(expected one of {', '.join(SUPPORTED_TYPES)})"
    )


def normalize_period(raw : str | None) -> str:
    """Map free-text term onto a STUDY_CAMPUS key; '' when unmatched (the
    empty string is stored as NULL, the existing convention).

    Case/whitespace-insensitive; tolerates "Semester" spelled out. Summer
    forms must carry the campus suffix: a bare "Year 1 Summer" is ambiguous
    and yields ''.
    """
    if raw is None:
        return ""
    cleaned = " ".join(str(raw).split())
    if not cleaned:
        return ""
    folded = cleaned.casefold()
    semester_folded = folded.replace("semester", "sem")
    for key in STUDY_CAMPUS:
        norm = " ".join(key.split()).casefold()
        if folded == norm or semester_folded == norm:
            return key
    return ""


def parse_llm_json(text : str) -> list[dict]:
    """Pull the JSON array out of an LLM reply; fences and prose tolerated.

    response_format=json_object is deliberately avoided - many OpenAI-
    compatible endpoints reject it - hence the tolerant slice-and-parse.
    A bare JSON object is an error, not a source of embedded arrays.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None # not a bare JSON value: fall through to slicing
    if parsed is None:
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            raise CourseImportError("LLM reply contains no JSON array.")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as e:
            raise CourseImportError(f"LLM reply is not valid JSON: {e}") from e
    if not isinstance(parsed, list):
        raise CourseImportError("LLM reply is not a JSON array.")
    return [row for row in parsed if isinstance(row, dict)]


def canonical_course_id(context : CourseDataContext, course_id : str) -> str:
    """Catalogue-canonical form of a transcript course id.

    HK ids pass through; SZ ids are reversed to their HK equivalent via a
    lookup over every major's equivalence map; anything unknown comes back
    unchanged and later lands in the unrecognized-warning bucket.
    Deliberately NOT _course_key(): a transcript spans majors, so no single
    major's mapping is authoritative.
    """
    cid = str(course_id).strip().upper()
    if not cid:
        return ""
    try:
        if determine_campus(cid) == "hk":
            return cid
    except DataLoadError:
        return cid
    for mapping in context.equivalence_courses.values():
        for hk_id, sz_id in mapping.items():
            if str(sz_id).upper() == cid:
                return str(hk_id).upper()
    return cid


def build_preview_rows(
    context : CourseDataContext,
    llm_rows : list[dict],
    existing : list[dict],
    major_2 : str,
) -> pd.DataFrame:
    """Raw LLM rows ({code,title,term,credits}) -> editable preview DataFrame.

    existing: rows from fetch_all_planned (all tables, tagged with 'source')
    feeding the read-only "Existing Period" column - a course may already be
    planned in any table, not just study_plan. Blank codes are dropped;
    duplicate canonical ids keep the first occurrence; unrecognized titles
    get a warning prefix so hallucinated courses cannot slip into the plan
    unnoticed.

    Credits: catalogue credits for recognized courses (the planner always
    derives those from the catalogue), the transcript's value for
    unrecognized ones - input-table rows persist it.
    """
    existing_period : dict[str, str] = {}
    for row in existing:
        cid = str(row.get("course_id") or "")
        period = row.get("study_period") or ""
        if cid and period and cid not in existing_period:
            existing_period[cid] = period
    records : list[dict] = []
    seen : set[str] = set()
    for row in llm_rows:
        cid = canonical_course_id(context, row.get("code") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        try:
            info = get_course_info(context, cid)
            title : str = info[0]
            recognized : bool = True
        except InfoMissingError:
            title = str(row.get("title") or "").strip() or cid
            recognized = False
        if recognized:
            try:
                credits : int | None = int(info[1])
            except (ValueError, IndexError):
                credits = None
        else:
            try:
                credits = int(row.get("credits"))
            except (TypeError, ValueError):
                credits = None
        records.append({
            "Course ID": cid,
            "Course": f"{cid} {title}" if recognized else f"⚠ {title}",
            "Recognized": recognized,
            "Existing Period": existing_period.get(cid, ""),
            "Study Period": normalize_period(row.get("term")),
            "Credits": credits,
            "Category": default_category(context, cid, major_2),
        })
    return pd.DataFrame(records, columns=pd.Index(PREVIEW_COLUMNS))


# --- LLM extraction ----------------------------------------------------------

def extract_courses(client : Any, images : list[bytes], model : str) -> list[dict]:
    """Send rendered pages to a vision LLM; returns parsed course rows.

    `client` is injected: the real OpenAI instance in production (built by
    _get_client), a fake in tests. Provider/network failures wrap into
    CourseImportError - no silent fallback.
    """
    content : list[dict] = [
        {"type": "text", "text": "Extract every course from this transcript."},
    ]
    for png in images:
        b64 = base64.b64encode(png).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )
    except CourseImportError:
        raise
    except Exception as e:
        raise CourseImportError(
            f"Course extraction request failed: {e}"
        ) from e
    text = response.choices[0].message.content or ""
    return parse_llm_json(text)


def extract_courses_from_secrets(images : list[bytes]) -> list[dict]:
    """Production entry point: build the real client from st.secrets, then
    delegate to extract_courses. Kept separate so tests inject a fake client
    into extract_courses without touching secrets or the network."""
    api_key, base_url, model = _llm_config()
    client = _get_client((api_key, base_url, model))
    return extract_courses(client, images, model)


# --- persistence --------------------------------------------------------------

def _in_catalogue(context : CourseDataContext, cid : str) -> bool:
    """True when the id resolves to a catalogue entry (HK id or its HK
    equivalent); prefix-routed ids never reach this check."""
    try:
        get_course_info(context, cid)
        return True
    except InfoMissingError:
        return False


# Tables whose rows carry a user-typed credits column (the University Core
# input sections); study_plan/english derive credits from the catalogue.
_INPUT_TABLES : frozenset[str] = frozenset({"pe", "college_ge", "four_area_ge"})

# Mirrors the defaults the University Core tab pre-fills for a new row.
_INPUT_TABLE_CREDIT_DEFAULTS : dict[str, int] = {
    "pe": 1, "college_ge": 3, "four_area_ge": 3,
}


def _input_table_course_id(cid : str, display : Any) -> str:
    """Input tables store the whole 'CODE Title' cell as course_id
    (user_input_on_change identity = the typed cell). Title is recovered
    from the preview's display column: 'CODE Title' when recognized,
    '⚠ Title' otherwise.
    """
    text = str(display or "").strip()
    if text.startswith("⚠ "):
        text = text[2:].strip()
    if text.casefold().startswith(cid.casefold()):
        text = text[len(cid):].strip()
    return f"{cid} {text}" if text else cid


def _clean_credits(value : Any, default : int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):  # None / '' / NaN
        return default

def write_confirmed(context : CourseDataContext, user_id : str, df : pd.DataFrame) -> int:
    """Persist confirmed preview rows, routed by the Category column.

    The preview is fully editable: the user may correct Course ID cells and
    re-target a row via the Category dropdown, so routing follows the
    (possibly edited) Category; a missing/stale category falls back to
    prefix + catalogue routing. Input-table categories (PE / College GE /
    Four Areas / English) import regardless of catalogue recognition - the
    user explicitly said where the course belongs. Study-plan categories
    require a catalogue entry: unknown ids are skipped (summarized in one
    st.info) - they need manual entry on their tab.

    Per-table identity conventions (mirroring how each tab saves rows):
    study_plan/english store the bare course code; the input tables store
    the 'CODE Title' cell and carry a credits column, so those rows get the
    transcript's credits (or the tab's default when absent).

    Per-row semantics mirror user_input_on_change: a failing row shows one
    st.error while already-written rows stay; returns the upsert count.
    Empty Study Period stores NULL.
    """
    count : int = 0
    skipped : list[str] = []
    for _, row in df.iterrows():
        cid = str(row["Course ID"] or "").strip().upper()
        if not cid:
            continue
        period = row["Study Period"]
        payload = {
            "id": user_id,
            "course_id": cid,
            "study_period": period if isinstance(period, str) and period.strip() else None,
        }
        category = row.get("Category")
        table : str | None = CATEGORY_TABLES.get(category) if isinstance(category, str) else None
        if table is None: # missing/stale category: derive it as best effort
            routed : tuple[str, str] | None = classify_course(cid)
            if routed is not None:
                table = routed[1]
            elif _in_catalogue(context, cid):
                table = "study_plan"
            else:
                skipped.append(cid)
                continue
        elif table == "study_plan" and not _in_catalogue(context, cid):
            skipped.append(cid)
            continue # unknown id: left for manual entry on the tabs
        try:
            upsert_data(user_id, payload, table_name=table)
        except Exception:
            st.error(f"Failed to import {cid}, please try again.")
            continue
        count += 1
    if skipped:
        st.info(
            "Skipped (not in the course catalogue, add them manually on the "
            f"corresponding tab): {', '.join(skipped)}"
        )
    return count
