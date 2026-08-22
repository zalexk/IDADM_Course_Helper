"""Planner tab: year-by-year credit breakdown, graduation requirements, overall view.

Replaces the production version's session_state-based approach with centralized
computation from Supabase saved data. No side effects — requirement status is
computed on the fly from the actual saved study plans.
"""

import streamlit as st
import pandas as pd

from src.data_retrieval import (
    CourseDataContext,
    get_course_list,
    get_course_info,
    get_major_2_requirement,
    convert_course_id,
    determine_campus,
    determine_level,
    InfoMissingError,
    _course_key,
)
from src.storage import fetch_all_planned
from src.pdf_generator import generate_study_plan_pdf
from src.word_generator import generate_study_plan_docx
from app.constant import STUDY_CAMPUS, GRADUATION_REQUIREMENT
from src.course_import import (
    IMPORT_CATEGORIES,
    MAX_PAGES,
    SUPPORTED_TYPES,
    CourseImportError,
    build_preview_rows,
    extract_courses_from_secrets,
    render_pages,
    write_confirmed,
)
from app.components import study_period_col_config

_IDA = "Interdisciplinary Data Analytics"


# ---------- helpers ----------

def _credits(context : CourseDataContext, course_id : str) -> int:
    """Look up a course's credit units; 0 if not in catalogue."""
    try:
        return int(get_course_info(context, course_id)[1])
    except (InfoMissingError, ValueError, IndexError):
        return 0


def _row_credits(row : dict) -> int:
    """Credit units from a saved row: the user-typed value (input tables) or 0."""
    try:
        return int(row.get("credits"))
    except (TypeError, ValueError):
        return 0


def _campus_code(context : CourseDataContext, cid : str, campus : str) -> str:
    """Course id as offered at `campus` ('CUHK'/'CUHKSZ'); original if no equivalent.

    The stored id is the canonical key (usually HK). Equivalence is per-major;
    try each major's bidict and take the first conversion that lands on the
    target campus.
    """
    target = "hk" if campus == "CUHK" else "sz"
    if determine_campus(cid) == target:
        return cid
    for major in context.equivalence_bidicts:
        try:
            converted = convert_course_id(context, major, cid)
            if determine_campus(converted) == target:
                return converted
        except InfoMissingError:
            continue
    return cid # no equivalent at that campus: keep the original id


def _check_credit_limit(year : int, sem : int, total_credit : int) -> None:
    """Show st.error if the credit load is outside the allowed range.

    sem: 1/2 = regular semester, 3 = summer, 0 = whole academic year.
    """
    upper, lower = 18, 9
    if sem == 3:
        upper, lower = 6, 0
    elif sem == 0:
        upper, lower = 39, 18
    elif year == 1:
        upper = 19

    if not (lower <= total_credit <= upper):
        st.error(
            f"You are over / under the course load ({lower} <= Credits <= {upper}).\n\n"
            "**You need to submit relevant applications for the approval**."
        )


def _build_course_table(context : CourseDataContext, all_rows : list[dict]) -> pd.DataFrame:
    """Build a unified DataFrame from all saved rows across all tables.

    Display id/title: each course is shown as offered at the campus of its
    study period (STUDY_CAMPUS), converted via equivalence when possible.
    Credits: input-table rows (pe/college_ge/four_area_ge) use the DB-stored
    user-typed value; catalogue rows (study_plan, no credits column) use the
    catalogue credit.
    """
    INPUT_SOURCES = {"pe", "college_ge", "four_area_ge"}
    records = []
    for row in all_rows:
        cid = row["course_id"]
        sp = row["study_period"] or ""
        campus = STUDY_CAMPUS.get(sp, "CUHK")
        display_id = _campus_code(context, cid, campus)
        title = ""
        try:
            title = get_course_info(context, display_id)[0]
        except (InfoMissingError, ValueError, IndexError):
            pass
        if row.get("source") in INPUT_SOURCES:
            credits = _row_credits(row)
        else:
            credits = _credits(context, cid)
        records.append({
            "Course": f"{display_id} {title}".strip(),
            "Credits": credits,
            "Study Period": sp,
        })
    return pd.DataFrame(records, columns=pd.Index(["Course", "Credits", "Study Period"]))


# ---------- year view ----------

def _year_view(all_courses : pd.DataFrame, year : int) -> None:
    sem1_period = f"Year {year} Sem 1"
    sem2_period = f"Year {year} Sem 2"
    sem1_campus = STUDY_CAMPUS[sem1_period]
    sem2_campus = STUDY_CAMPUS[sem2_period]
    periods_for_year = [sem1_period, sem2_period]
    sem_cap = 19 if year == 1 else 18

    sem1, sem2 = st.columns(2)

    with sem1:
        st.subheader(f"Sem 1 ({sem1_campus})")
        filtered = all_courses[all_courses["Study Period"] == sem1_period]
        total = int(filtered["Credits"].sum())
        _check_credit_limit(year, 1, total)
        st.dataframe(filtered[["Course", "Credits"]], hide_index=True, height="content")
        st.metric("Subtotal Credits", value=total, delta=sem_cap - total)

    with sem2:
        st.subheader(f"Sem 2 ({sem2_campus})")
        filtered = all_courses[all_courses["Study Period"] == sem2_period]
        total = int(filtered["Credits"].sum())
        _check_credit_limit(year, 2, total)
        st.dataframe(filtered[["Course", "Credits"]], hide_index=True, height="content")
        st.metric("Subtotal Credits", value=total, delta=18 - total)

    if year < 4:
        summer_col, year_col = st.columns(2)

        with summer_col:
            summer_periods = [f"Year {year} Summer (CUHK)", f"Year {year} Summer (CUHKSZ)"]
            periods_for_year.extend(summer_periods)
            st.subheader("Summer Session")
            filtered = all_courses[all_courses["Study Period"].isin(summer_periods)]
            total = int(filtered["Credits"].sum())
            _check_credit_limit(year, 3, total)
            st.dataframe(filtered[["Course", "Credits"]], hide_index=True, height="content")
            st.metric("Subtotal Credits", value=total, delta=6 - total)

        with year_col:
            st.subheader("Whole Academic Year")
            filtered = all_courses[all_courses["Study Period"].isin(periods_for_year)]
            total = int(filtered["Credits"].sum())
            st.metric("Total Credits for the Year", value=total, delta=39 - total)
            _check_credit_limit(year, 0, total)

    else:
        st.subheader("Whole Academic Year")
        filtered = all_courses[all_courses["Study Period"].isin(periods_for_year)]
        total = int(filtered["Credits"].sum())
        st.metric("Total Credits for the Year", value=total, delta=39 - total)
        _check_credit_limit(year, 0, total)


# ---------- requirement computation ----------

def _compute_ucore(context : CourseDataContext, all_rows : list[dict]) -> dict[str, bool]:
    """Check University Core requirements from saved data."""
    req = GRADUATION_REQUIREMENT["University Core"]
    ucore_list = get_course_list(context, "University Core")["Required Courses"]
    planned_ucore = {_course_key(context, "University Core", c) for c in ucore_list}
    # planned_ucore only contains keys from the Required Courses catalogue;
    # we need the FULL set of saved course_ids to check against.
    planned_ids = {r["course_id"] for r in all_rows}
    planned_ucore &= planned_ids

    status : dict[str, bool] = {}

    # Specific course checks (all HK courses, canonical key = self)
    status["GE: Foundation Courses"] = {"UGFH1000", "UGFN1000"}.issubset(planned_ucore)
    status["Understanding China"] = "UGCP1001" in planned_ucore
    status["Hong Kong in the Wider Constitutional Order"] = "UGCP1002" in planned_ucore
    status["Digital Literacy and Computational Thinking"] = "ENGG1003" in planned_ucore

    # Credit-based from user-input tables (credits = user-typed value in DB)
    pe_credits = sum(_row_credits(r) for r in all_rows if r.get("source") == "pe")
    college_ge_credits = sum(_row_credits(r) for r in all_rows if r.get("source") == "college_ge")
    four_area_credits = sum(_row_credits(r) for r in all_rows if r.get("source") == "four_area_ge")
    # Chinese Language is a fixed catalogue section (identity = canonical HK
    # key); count catalogue credits for its keys present in study_plan.
    chinese_keys = {
        _course_key(context, "University Core", c)
        for c in get_course_list(context, "University Core")["Chinese Language"]
    }
    chinese_credits = sum(
        _credits(context, r["course_id"]) for r in all_rows
        if r.get("source") == "study_plan" and r["course_id"] in chinese_keys
    )
    # Catalogue credits (all ELTU/ENG codes are in course_list.csv); DB-stored
    # credits are ignored - the fixed English table and course-import rows
    # never persist a credits value.
    english_credits = sum(
        _credits(context, r["course_id"]) for r in all_rows
        if r.get("source") == "english"
    )

    status["Physical Education"] = pe_credits >= req["Physical Education"]
    status["College GE"] = college_ge_credits >= req["College GE"]
    status["GE: Four Areas (Area A, C, D)"] = four_area_credits >= req["GE: Four Areas (Area A, C, D)"]
    status["Chinese Language"] = chinese_credits >= req["Chinese Language"]
    status["English Language"] = english_credits >= req["English Language"]

    return status


def _compute_major_1(context : CourseDataContext, planned_ids : set[str], major_2 : str) -> dict[str, list]:
    """Check 1st Major (IDA) requirements from saved data."""
    req = GRADUATION_REQUIREMENT["1st Major"]
    status : dict[str, list] = {}

    # Fixed sections: all courses planned?
    for cat in ("Faculty Package", "Required Courses", "COOP"):
        course_list = get_course_list(context, _IDA)[cat]
        keys = [_course_key(context, _IDA, c) for c in course_list]
        planned_count = sum(1 for k in keys if k in planned_ids)
        credits = sum(_credits(context, k) for k in keys if k in planned_ids)
        if cat == "COOP":
            status[cat] = [True, 3]  # compulsory
        else:
            status[cat] = [planned_count == len(keys), credits]

    # Electives (course list from major_2, equivalence via IDA)
    elective_groups = get_course_list(context, major_2)["1st Major Elective Courses"]
    group_a = elective_groups["A"]
    group_b = elective_groups["B"]

    a_keys = [_course_key(context, _IDA, c) for c in group_a]
    b_keys = [_course_key(context, _IDA, c) for c in group_b]
    a_credits = sum(_credits(context, k) for k in a_keys if k in planned_ids)
    b_credits = sum(_credits(context, k) for k in b_keys if k in planned_ids)
    total_elective = a_credits + b_credits

    status["Elective Group A"] = [a_credits >= req["Elective Group A"], a_credits]
    status["Elective Group B"] = [b_credits >= req["Elective Group B"], b_credits]
    status["Elective"] = [total_elective >= req["Elective"], total_elective]

    # Level checks
    level_3_credits = 0
    level_4_credits = 0
    for cid in group_a + group_b:
        key = _course_key(context, _IDA, cid)
        if key in planned_ids:
            level = determine_level(cid)
            credits = _credits(context, key)
            if level == 4:
                level_4_credits += credits
            elif level == 3:
                level_3_credits += credits

    status["Elective (4000)"] = [level_4_credits >= req["Elective (4000)"], level_4_credits]
    status["Elective (3000+)"] = [
        (level_3_credits + level_4_credits) >= req["Elective (3000+)"],
        level_3_credits + level_4_credits,
    ]

    return status


def _compute_major_2(context : CourseDataContext, planned_ids : set[str], major_2 : str) -> dict[str, list]:
    """Check 2nd Major requirements from saved data."""
    status : dict[str, list] = {}

    # Required Courses: all planned?
    req_list = get_course_list(context, major_2)["Required Courses"]
    req_keys = [_course_key(context, major_2, c) for c in req_list]
    req_planned = sum(1 for k in req_keys if k in planned_ids)
    req_credits = sum(_credits(context, k) for k in req_keys if k in planned_ids)
    status["Required Courses"] = [req_planned == len(req_keys), req_credits]

    # Research Component: all planned?
    research_list = get_course_list(context, major_2)["Research Component"]
    research_keys = [_course_key(context, major_2, c) for c in research_list]
    research_planned = sum(1 for k in research_keys if k in planned_ids)
    research_credits = sum(_credits(context, k) for k in research_keys if k in planned_ids)
    status["Research Component"] = [research_planned == len(research_keys), research_credits]

    # 2nd Major Elective: credits >= threshold
    elective_list = get_course_list(context, major_2)["2nd Major Elective Courses"]
    elective_keys = [_course_key(context, major_2, c) for c in elective_list]
    elective_credits = sum(_credits(context, k) for k in elective_keys if k in planned_ids)
    threshold = get_major_2_requirement(context, major_2, "Elective Courses")
    status["2nd Major Elective Courses"] = [elective_credits >= threshold, elective_credits]

    return status


# ---------- requirement view ----------

def _requirement_view(
    context : CourseDataContext,
    all_rows : list[dict],
    major_2 : str,
) -> None:
    st.header("Graduation Requirements")

    planned_ids = {r["course_id"] for r in all_rows}
    total_credits = sum(
        _row_credits(r) if r.get("source") in {"pe", "college_ge", "four_area_ge"}
        else _credits(context, r["course_id"])
        for r in all_rows
    )

    ucore_status = _compute_ucore(context, all_rows)
    major1_status = _compute_major_1(context, planned_ids, major_2)
    major2_status = _compute_major_2(context, planned_ids, major_2)

    ucore_col, major_col = st.columns(2)

    with ucore_col:
        st.subheader("University Core")
        ucore_req = GRADUATION_REQUIREMENT["University Core"]
        st.dataframe(
            pd.DataFrame({
                "Item": list(ucore_req.keys()),
                "Requirement": list(ucore_req.values()),
                "Fulfil": [ucore_status.get(item, False) for item in ucore_req],
            }),
            hide_index=True,
            height="content",
        )

    with major_col:
        st.subheader("1st Major (IDA)")
        major1_req = GRADUATION_REQUIREMENT["1st Major"]
        st.dataframe(
            pd.DataFrame({
                "Item": list(major1_req.keys()),
                "Requirement": list(major1_req.values()),
                "Credits": [major1_status[item][1] for item in major1_req],
                "Fulfil": [major1_status[item][0] for item in major1_req],
            }),
            hide_index=True,
            height="content",
        )

        st.subheader(f"2nd Major ({major_2})")
        st.dataframe(
            pd.DataFrame({
                "Item": list(major2_status.keys()),
                "Requirement": [
                    (GRADUATION_REQUIREMENT["Research Component"] if item == "Research Component"
                     else get_major_2_requirement(context, major_2, "Elective Courses") if item == "2nd Major Elective Courses"
                     else "All required")
                    for item in major2_status
                ],
                "Credits": [major2_status[item][1] for item in major2_status],
                "Fulfil": [major2_status[item][0] for item in major2_status],
            }),
            hide_index=True,
            height="content",
        )

    st.metric(
        "Total Credit",
        value=total_credits,
        delta=GRADUATION_REQUIREMENT["Total Credit"] - total_credits,
    )


# ---------- overall view ----------

def _overall_view(all_courses : pd.DataFrame, major_2 : str) -> None:
    st.info("You can view and export your overall study plan here.")

    col_pdf, col_word = st.columns(2)

    with col_pdf:
        try:
            pdf_bytes = generate_study_plan_pdf(all_courses, major_2, user_tz=st.context.timezone)
            st.download_button(
                label="Export as PDF",
                data=pdf_bytes,
                file_name=f"Study Plan - {major_2}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Failed to prepare PDF: {e}")

    with col_word:
        try:
            word_stream = generate_study_plan_docx(all_courses, major_2, user_tz=st.context.timezone)
            st.download_button(
                label="Export as Word",
                data=word_stream,
                file_name=f"Study Plan - {major_2}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as e:
            st.error(f"Failed to prepare Word doc: {e}")

    st.dataframe(all_courses, hide_index=True, height="content")

# ---------- course import ----------

def _import_courses(context : CourseDataContext, user_id : str, major_2 : str) -> None:
    """Batch-import previously-taken courses from a transcript image/PDF.

    Parse stores the preview in session state; the editor below has no
    on_change - edits land in the returned DataFrame and are read at Confirm.
    """
    with st.expander("📥 Import Courses (導入已讀課程)"):
        st.info("Recommend to use the screenshot of ***Academic Records*** from CUSIS")
        imported : int | None = st.session_state.pop("course-imported", None)
        if imported is not None:
            st.success(f"Imported {imported} courses.")
        uploaded = st.file_uploader(
            "Screenshot or PDF",
            type=list(SUPPORTED_TYPES),
            max_upload_size = 5
        )
        if uploaded is None:
            return
        file_bytes = uploaded.getvalue()
        if len(file_bytes) > 10 * 1024 * 1024:
            st.error("File exceeds 10 MB, please upload a smaller file.")
            return

        if st.button("Import"):
            try:
                pages = render_pages(file_bytes, uploaded.name)
                if len(pages) == MAX_PAGES and uploaded.name.casefold().endswith(".pdf") \
                        and _pdf_page_count(file_bytes) > MAX_PAGES:
                    st.warning(f"Only the first {MAX_PAGES} pages were parsed.")
                llm_rows = extract_courses_from_secrets(pages)
                st.session_state["course-import-preview"] = build_preview_rows(
                    context, llm_rows, fetch_all_planned(user_id), major_2,
                )
            except CourseImportError as e:
                st.error(f"Course import failed: {e}")

        preview = st.session_state.get("course-import-preview")
        if preview is None or preview.empty:
            if preview is not None:
                st.warning("No courses were recognized in this document.")
            return

        st.markdown(
            "**Check before confirming**\n"
            "- **Course ID** — editable: fix any misread code here.\n"
            "- **Recognized** — ✓ means the code was found in the course "
            "catalogue. Unrecognized rows (⚠) are only imported when their "
            "category is a University Core input section "
            "(PE / College GE / Four Areas / English); otherwise they are "
            "skipped and must be added manually on that tab.\n"
            "- **Existing Period** — the period already saved in your plan "
            "for this course (read-only, blank = not planned yet). "
            "Confirming overwrites it with the **Study Period** below.\n"
            "- **Study Period** — the period that will be saved when you "
            "confirm.\n"
            "- **Credits** — credit units from your transcript. Only saved "
            "for University Core input sections (PE / College GE / Four "
            "Areas); other categories always use the catalogue credits.\n"
            "- **Category** — the requirement section this course counts "
            "towards; change it with the dropdown if the suggestion is wrong."
        )

        edited = st.data_editor(
            preview,
            hide_index=True,
            height="content",
            column_config={
                **study_period_col_config,
                "Credits": st.column_config.NumberColumn(
                    "Credits",
                    width="small",
                    min_value=0,
                    max_value=10,
                    step="int", # type: ignore[return-value]
                    help="Credit units from the transcript; saved only for "
                         "PE / College GE / Four Areas entries.",
                ),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(IMPORT_CATEGORIES),
                    help="The requirement section this course counts towards.",
                ),
            },
            disabled=["Course", "Recognized", "Existing Period"],
            key="course-import-editor",
        )

        if st.button("Confirm import"):
            count = write_confirmed(context, user_id, edited)
            del st.session_state["course-import-preview"]
            st.session_state["course-imported"] = count
            st.rerun()


def _pdf_page_count(file_bytes : bytes) -> int:
    """Page count for the truncation warning; 0 when unreadable."""
    import pypdfium2 as pdfium
    try:
        return len(pdfium.PdfDocument(file_bytes))
    except Exception:
        return 0

# ---------- entry point ----------

def ui(context : CourseDataContext, major_2 : str) -> None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in to view your study plan.")
        return
    _import_courses(context, user_id, major_2)

    all_rows = fetch_all_planned(user_id)
    all_courses = _build_course_table(context, all_rows)

    y1, y2, y3, y4, grad_req, overall = st.tabs([
        "Year 1", "Year 2", "Year 3", "Year 4",
        "Graduation Requirements", "Overall",
    ])

    with y1:
        _year_view(all_courses, 1)
    with y2:
        _year_view(all_courses, 2)
    with y3:
        _year_view(all_courses, 3)
    with y4:
        _year_view(all_courses, 4)
    with grad_req:
        _requirement_view(context, all_rows, major_2)
    with overall:
        _overall_view(all_courses, major_2)
