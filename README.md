# Attendance Analysis Agent

**Use case:** Tracks attendance and predicts eligibility.

A Flask web app that ingests subject-wise attendance records and tells you,
per student, whether they're eligible to sit the exam under the standard
75% attendance rule — and if not, whether they can still make it.

---

## 1. Problem statement

Colleges enforce a minimum attendance percentage (commonly **75%**) for exam
eligibility. Manually checking this across every subject for every student
is slow and error-prone, and students rarely know in advance whether they
can still recover if they've fallen behind. This agent automates both the
tracking and the prediction.

## 2. What it does

1. **Tracks** — Upload a CSV of subject-wise attendance (`ClassesHeld`,
   `ClassesAttended` per student per subject). The agent aggregates this
   into an overall attendance percentage per student.
2. **Predicts eligibility** — For every student it classifies them into
   one of three verdicts:
   | Verdict | Meaning |
   |---|---|
   | **Eligible** | Current attendance is already ≥ 75%. The report also shows how many more classes they can safely miss. |
   | **At Risk** | Currently below 75%, but mathematically still able to cross 75% if they attend every remaining class. The report shows exactly how many classes in a row they must attend. |
   | **Not Eligible** | Even with 100% attendance for every remaining class, they cannot reach 75%. |

## 3. Prediction logic (the "agent" brain)

This is a deterministic, explainable rule-based engine — not a black-box
ML model — which makes it accurate and easy to defend in a viva:

```
current_pct        = attended / held * 100
max_possible_pct    = (attended + remaining) / (held + remaining) * 100

if current_pct >= 75:
    status = "Eligible"
    safe_bunks = floor(attended / 0.75 - held)          # classes they can still skip

elif max_possible_pct < 75:
    status = "Not Eligible"                              # can never recover

else:
    status = "At Risk"
    classes_needed = smallest x such that
                      (attended + x) / (held + x) >= 0.75
```

`remaining` is the number of classes still expected to be held this
semester, entered on the upload form (default 20).

## 4. Tech stack

- **Backend:** Python 3, Flask
- **Data processing:** pandas
- **Frontend:** Jinja2 templates, plain HTML/CSS (no JS framework needed)
- **Design theme:** "Academic Register" — the dashboard is styled like a
  physical attendance ledger, with verdicts shown as ink-stamp badges.

## 5. Project structure

```
attendance_analysis_agent/
├── app.py                       # Flask app + prediction engine
├── requirements.txt
├── static/
│   ├── style.css
│   └── sample_attendance.csv    # demo dataset (8 students, 3 subjects)
└── templates/
    ├── index.html               # upload form
    └── dashboard.html           # results / eligibility report
```

## 6. How to run

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser, upload
`static/sample_attendance.csv` (or your own CSV in the same format), and
click **Analyze attendance**.

## 7. CSV format required

```
RollNo,Name,Subject,ClassesHeld,ClassesAttended
101,Arun Kumar,Mathematics,40,38
101,Arun Kumar,Physics,35,33
102,Divya Sri,Mathematics,40,25
```

One row per student per subject. The agent sums across subjects to get
each student's overall attendance.

## 8. Possible extensions (for viva / future scope)

- Add login for faculty vs. student views.
- Store historical data in a database (SQLite/PostgreSQL) instead of
  re-uploading a CSV each time, so trends over the semester can be charted.
- Send automatic email/SMS alerts to "At Risk" students.
- Replace the rule-based `remaining_classes` assumption with actual academic
  calendar data per subject for a more precise projection.
- Add a real ML layer (e.g. logistic regression on historical semesters) to
  predict *drop-off risk* rather than just doing threshold arithmetic.

---
**Author:** Your Name Here
**Course / Dept:** _____________
