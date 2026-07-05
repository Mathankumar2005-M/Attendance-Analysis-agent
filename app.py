"""
Attendance Analysis Agent
-------------------------
Use case: Tracks attendance and predicts eligibility.

This Flask app ingests subject-wise attendance records (CSV), aggregates them
per student, and runs a rule-based prediction engine that answers three
questions colleges actually care about:

    1. Is the student currently eligible (>=75% attendance)?
    2. If not, CAN they still become eligible before the semester ends,
       assuming perfect attendance from today onward?
    3. If yes (already eligible), how many more classes can they safely
       miss and still stay eligible?

Author: Attendance Analysis Agent
"""

import io
import os
import uuid

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "attendance-analysis-agent-secret"

ELIGIBILITY_THRESHOLD = 75.0  # percent, standard academic norm

REQUIRED_COLUMNS = {"RollNo", "Name", "Subject", "ClassesHeld", "ClassesAttended"}


# ----------------------------------------------------------------------------
# Core prediction engine
# ----------------------------------------------------------------------------
def analyze_attendance(df: pd.DataFrame, remaining_classes: int):
    """
    Aggregates per-student attendance across subjects and predicts eligibility.

    Parameters
    ----------
    df : DataFrame with columns RollNo, Name, Subject, ClassesHeld, ClassesAttended
    remaining_classes : int
        Number of classes still expected to be held this semester (per subject
        average, applied uniformly for the overall prediction).

    Returns
    -------
    list[dict] : one row per student, ready for the dashboard template
    """
    grouped = (
        df.groupby(["RollNo", "Name"], as_index=False)[["ClassesHeld", "ClassesAttended"]]
        .sum()
    )

    results = []
    for _, row in grouped.iterrows():
        held = int(row["ClassesHeld"])
        attended = int(row["ClassesAttended"])
        current_pct = round((attended / held) * 100, 2) if held else 0.0

        future_held = held + remaining_classes
        future_attended_best_case = attended + remaining_classes
        max_possible_pct = (
            round((future_attended_best_case / future_held) * 100, 2)
            if future_held
            else 0.0
        )

        classes_needed = 0
        safe_bunks = 0
        status = ""

        if current_pct >= ELIGIBILITY_THRESHOLD:
            status = "Eligible"
            # how many more classes can be missed and still stay >= 75%
            # (attended) / (held + skip) >= 0.75  =>  skip <= attended/0.75 - held
            safe_bunks = int((attended / (ELIGIBILITY_THRESHOLD / 100)) - held)
            safe_bunks = max(safe_bunks, 0)
        elif max_possible_pct < ELIGIBILITY_THRESHOLD:
            status = "Not Eligible"
        else:
            status = "At Risk"
            # smallest x (classes attended consecutively from now) such that
            # (attended + x) / (held + x) >= 0.75
            x = 0
            for candidate in range(0, remaining_classes + 1):
                if held + candidate == 0:
                    continue
                pct = (attended + candidate) / (held + candidate)
                if pct >= ELIGIBILITY_THRESHOLD / 100:
                    x = candidate
                    break
            classes_needed = x

        results.append(
            {
                "roll_no": row["RollNo"],
                "name": row["Name"],
                "held": held,
                "attended": attended,
                "current_pct": current_pct,
                "max_possible_pct": max_possible_pct,
                "status": status,
                "classes_needed": classes_needed,
                "safe_bunks": safe_bunks,
            }
        )

    # Sort: Not Eligible first, then At Risk, then Eligible -> most actionable first
    order = {"Not Eligible": 0, "At Risk": 1, "Eligible": 2}
    results.sort(key=lambda r: (order[r["status"]], r["current_pct"]))
    return results


def subject_breakdown(df: pd.DataFrame):
    """Per-subject attendance % for every student, used for the detail view."""
    df = df.copy()
    df["Pct"] = round((df["ClassesAttended"] / df["ClassesHeld"]) * 100, 2)
    return df.to_dict(orient="records")


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("csv_file")
    remaining_classes = request.form.get("remaining_classes", "20")

    try:
        remaining_classes = int(remaining_classes)
    except ValueError:
        remaining_classes = 20

    if not file or file.filename == "":
        flash("Please choose a CSV file first.")
        return redirect(url_for("index"))

    try:
        raw = file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(raw))
    except Exception as exc:
        flash(f"Could not read that CSV: {exc}")
        return redirect(url_for("index"))

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        flash(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
        return redirect(url_for("index"))

    df["ClassesHeld"] = pd.to_numeric(df["ClassesHeld"], errors="coerce").fillna(0)
    df["ClassesAttended"] = pd.to_numeric(df["ClassesAttended"], errors="coerce").fillna(0)

    students = analyze_attendance(df, remaining_classes)
    subjects = subject_breakdown(df)

    total = len(students)
    eligible_count = sum(1 for s in students if s["status"] == "Eligible")
    at_risk_count = sum(1 for s in students if s["status"] == "At Risk")
    not_eligible_count = sum(1 for s in students if s["status"] == "Not Eligible")

    summary = {
        "total": total,
        "eligible": eligible_count,
        "at_risk": at_risk_count,
        "not_eligible": not_eligible_count,
    }

    return render_template(
        "dashboard.html",
        students=students,
        subjects=subjects,
        summary=summary,
        remaining_classes=remaining_classes,
        threshold=ELIGIBILITY_THRESHOLD,
    )


@app.route("/sample")
def sample():
    """Serves the bundled sample CSV path info (used by a link on the homepage)."""
    return redirect(url_for("static", filename="sample_attendance.csv"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)