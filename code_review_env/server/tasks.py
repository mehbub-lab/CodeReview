"""
Task definitions for the Code Review Environment.

Each task contains a Python code snippet with planted bugs.
Each bug has metadata for deterministic grading.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Bug:
    """A planted bug in a code snippet."""

    id: str
    line_number: int
    bug_type: str
    severity: str  # "critical", "major", "minor"
    description: str
    keywords: List[str]
    fix_keywords: List[str]
    points: float  # scoring weight


@dataclass
class Task:
    """A code review task."""

    name: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    filename: str
    language: str
    code: str
    bugs: List[Bug]
    max_steps: int
    max_score: float = 0.0

    def __post_init__(self):
        self.max_score = sum(b.points for b in self.bugs)


# ---------------------------------------------------------------------------
# EASY TASK — "single_bug"
# Two clear bugs in a short student-grade processing function (~30 lines)
# ---------------------------------------------------------------------------

EASY_CODE = '''\
def process_students(students):
    """Process student records and return summary statistics."""
    if not students:
        return None

    total_grade = 0
    highest_grade = 0
    passing_students = []

    for student in students:
        name = student["name"]
        grade = student["grade"]

        total_grade += grade

        if grade > highest_grade:
            highest_grade = grade

        if grade >= 60:
            passing_students.append(name)

    average_grade = total_grade // len(students)

    return {
        "average": average_grade,
        "highest": highest_grade,
        "passing": passing_students,
        "pass_rate": len(passing_students) / len(students) * 100,
        "total_students": len(students),
    }


def format_report(stats):
    """Format statistics into a readable report string."""
    if stats is None:
        return "No data available"

    report = f"Class Report\\n"
    report += f"============\\n"
    report += f"Total Students: {stats['total_students']}\\n"
    report += f"Average Grade: {stats['average']:.1f}\\n"
    report += f"Highest Grade: {stats['highest']}\\n"
    report += f"Pass Rate: {stats['pass_rate']:.1f}%\\n"
    report += f"Passing Students:\\n"

    for i in range(len(stats["passing"])):
        report += f"  {i}. {stats['passing'][i]}\\n"

    return report
'''

EASY_BUGS = [
    Bug(
        id="easy_integer_division",
        line_number=23,
        bug_type="logic_error",
        severity="major",
        description="Integer division (//) truncates the average. Should use / for float division.",
        keywords=[
            "integer division",
            "//",
            "truncat",
            "floor division",
            "float division",
            "true division",
            "precision",
        ],
        fix_keywords=["/", "float", "true division", "regular division"],
        points=2.0,
    ),
    Bug(
        id="easy_off_by_one_index",
        line_number=46,
        bug_type="off_by_one",
        severity="minor",
        description="Loop index starts at 0, so student numbering starts at 0 instead of 1. Should use i+1.",
        keywords=[
            "off by one",
            "off-by-one",
            "index",
            "start at 0",
            "starts at 0",
            "zero-index",
            "zero index",
            "numbering",
            "i + 1",
            "i+1",
            "1-based",
            "1-index",
            "enumerate",
        ],
        fix_keywords=["i + 1", "i+1", "enumerate", "1-based", "start=1"],
        points=1.0,
    ),
]

EASY_TASK = Task(
    name="single_bug",
    description=(
        "Review this Python code that processes student grade records.\n"
        "Find all bugs, state the line number, describe the issue, and suggest a fix.\n"
        "There are 2 bugs to find."
    ),
    difficulty="easy",
    filename="student_grades.py",
    language="python",
    code=EASY_CODE,
    bugs=EASY_BUGS,
    max_steps=5,
)


# ---------------------------------------------------------------------------
# MEDIUM TASK — "multi_bug"
# Four bugs in a CSV employee data processor (~55 lines)
# ---------------------------------------------------------------------------

MEDIUM_CODE = '''\
import csv
import os
from datetime import datetime


def read_employee_data(filepath):
    """Read employee data from a CSV file and return processed records."""
    if not os.path.exists(filepath):
        return []

    employees = []
    file = open(filepath, "r")
    reader = csv.DictReader(file)

    for row in reader:
        try:
            name = row["name"].strip()
            age = int(row["age"])
            salary = float(row["salary"])
            department = row["department"].strip()
            hire_date = row["hire_date"]

            if age < 18 and age > 65:
                print(f"Warning: Invalid age {age} for {name}")
                continue

            hire = datetime.strptime(hire_date, "%Y-%m-%d")
            years = (datetime.now() - hire).days / 365

            employees.append(
                {
                    "name": name,
                    "age": age,
                    "salary": salary,
                    "department": department,
                    "hire_date": hire_date,
                    "years_of_service": round(years, 1),
                }
            )

        except KeyError as e:
            print(f"Missing field in row: {e}")
        except ValueError:
            print(f"Invalid data in row: {row}")

    return employees


def generate_department_report(employees):
    """Generate salary statistics by department."""
    if not employees:
        return {}

    departments = {}

    for emp in employees:
        dept = emp["department"]
        salary = emp["salary"]

        if dept not in departments:
            departments[dept] = {"total": 0, "count": 0, "employees": []}

        departments[dept]["total"] += salary
        departments[dept]["count"] += 1
        departments[dept]["employees"].append(emp["name"])

    report = {}
    for dept, data in departments.items():
        report[dept] = {
            "average_salary": data["total"] / data["count"],
            "employee_count": data["count"],
            "employees": data["employees"],
        }

    return report
'''

MEDIUM_BUGS = [
    Bug(
        id="med_resource_leak",
        line_number=13,
        bug_type="resource_leak",
        severity="major",
        description=(
            "File opened with open() but never closed. "
            "Should use a 'with' statement (context manager) to ensure the file is closed."
        ),
        keywords=[
            "resource leak",
            "file not closed",
            "never closed",
            "context manager",
            "with statement",
            "with open",
            "close",
            "leak",
            "not closed",
        ],
        fix_keywords=[
            "with open",
            "context manager",
            "file.close",
            "finally",
        ],
        points=2.0,
    ),
    Bug(
        id="med_logic_and_or",
        line_number=24,
        bug_type="logic_error",
        severity="critical",
        description=(
            "Condition 'age < 18 and age > 65' is always False (no number is both < 18 AND > 65). "
            "Should be 'or' instead of 'and'."
        ),
        keywords=[
            "always false",
            "impossible",
            "and",
            "or",
            "logic error",
            "logical error",
            "condition",
            "never true",
            "both",
            "impossible condition",
        ],
        fix_keywords=["or", "||", "age < 18 or age > 65"],
        points=3.0,
    ),
    Bug(
        id="med_no_file_close",
        line_number=44,
        bug_type="error_handling",
        severity="minor",
        description=(
            "The function returns employees but the file handle opened on line 13 "
            "is never closed, even on normal exit path."
        ),
        keywords=[
            "return",
            "file handle",
            "not closed",
            "cleanup",
            "finally",
            "leak",
        ],
        fix_keywords=["with", "finally", "close"],
        points=1.0,
    ),
    Bug(
        id="med_username_leak",
        line_number=24,
        bug_type="validation",
        severity="major",
        description=(
            "Invalid age validation silently continues, potentially allowing "
            "negative ages (the condition is always False due to the and/or bug)."
        ),
        keywords=[
            "negative",
            "validation",
            "silently",
            "skip",
            "invalid",
            "not validated",
            "negative age",
        ],
        fix_keywords=["raise", "ValueError", "validate", "check"],
        points=2.0,
    ),
]

MEDIUM_TASK = Task(
    name="multi_bug",
    description=(
        "Review this Python CSV processing code for an employee data system.\n"
        "Find all bugs, explain each one with its line number, severity, "
        "and suggest how to fix it.\nThere are 4 bugs to find."
    ),
    difficulty="medium",
    filename="employee_data.py",
    language="python",
    code=MEDIUM_CODE,
    bugs=MEDIUM_BUGS,
    max_steps=8,
)


# ---------------------------------------------------------------------------
# HARD TASK — "full_review"
# Six bugs in a task-management class with SQL, files, datetime (~90 lines)
# ---------------------------------------------------------------------------

HARD_CODE = '''\
import json
import os
import sqlite3
from datetime import datetime


class TaskManager:
    """A simple task management system backed by SQLite."""

    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._setup_db()

    def _setup_db(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT \'medium\',
                status TEXT DEFAULT \'pending\',
                created_at TEXT,
                due_date TEXT,
                assigned_to TEXT
            )
        """
        )
        self.conn.commit()

    def add_task(self, title, description="", priority="medium",
                 due_date=None, assigned_to=None):
        cursor = self.conn.cursor()
        query = (
            f"INSERT INTO tasks "
            f"(title, description, priority, status, created_at, due_date, assigned_to) "
            f"VALUES (\'{title}\', \'{description}\', \'{priority}\', \'pending\', "
            f"\'{datetime.now()}\', \'{due_date}\', \'{assigned_to}\')"
        )
        cursor.execute(query)
        self.conn.commit()
        return cursor.lastrowid

    def get_tasks(self, status=None, priority=None):
        cursor = self.conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += f" AND status = \'{status}\'"
        if priority:
            query += " AND priority = ?"
            params.append(priority)

        cursor.execute(query, params)
        return cursor.fetchall()

    def complete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status = \'done\' WHERE id = ?", (task_id,)
        )
        self.conn.commit()

    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_overdue_tasks(self):
        cursor = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT * FROM tasks WHERE due_date < ? AND status = \'pending\'",
            (today,),
        )
        tasks = cursor.fetchall()

        overdue = []
        for task in tasks:
            days_overdue = (
                datetime.now() - datetime.strptime(task[6], "%Y-%m-%d")
            ).days
            overdue.append({"task": task, "days_overdue": days_overdue})
        return overdue

    def export_tasks(self, filepath):
        tasks = self.get_tasks()
        task_dicts = []
        for task in tasks:
            task_dicts.append(
                {
                    "id": task[0],
                    "title": task[1],
                    "description": task[2],
                    "priority": task[3],
                    "status": task[4],
                    "created_at": task[5],
                    "due_date": task[6],
                    "assigned_to": task[7],
                }
            )

        with open(filepath, "w") as f:
            json.dump(task_dicts, f)

        return len(task_dicts)

    def __del__(self):
        self.conn.close()
'''

HARD_BUGS = [
    Bug(
        id="hard_sql_injection_add",
        line_number=38,
        bug_type="security",
        severity="critical",
        description=(
            "SQL injection vulnerability: user input (title, description, etc.) "
            "is directly interpolated into SQL via f-string instead of using "
            "parameterized queries."
        ),
        keywords=[
            "sql injection",
            "injection",
            "f-string",
            "f\"",
            "format string",
            "interpolat",
            "parameterized",
            "user input",
            "unsanitized",
            "sanitiz",
            "security",
        ],
        fix_keywords=[
            "parameterized",
            "placeholder",
            "?",
            "bind",
            "prepared statement",
            "cursor.execute(query, params",
            "cursor.execute(query, (",
        ],
        points=3.0,
    ),
    Bug(
        id="hard_sql_injection_get",
        line_number=51,
        bug_type="security",
        severity="critical",
        description=(
            "Another SQL injection: the status filter is interpolated via f-string "
            "while priority correctly uses a parameterized query. Inconsistent and vulnerable."
        ),
        keywords=[
            "sql injection",
            "injection",
            "status",
            "f-string",
            "inconsistent",
            "parameterized",
            "mixed",
        ],
        fix_keywords=["?", "parameterized", "placeholder", "params.append"],
        points=3.0,
    ),
    Bug(
        id="hard_delete_no_check",
        line_number=67,
        bug_type="logic_error",
        severity="major",
        description=(
            "delete_task does not verify that the task exists before deleting. "
            "No return value or feedback. Silently succeeds even if task_id doesn't exist."
        ),
        keywords=[
            "no check",
            "no verification",
            "silent",
            "exists",
            "rowcount",
            "feedback",
            "return",
            "no return",
            "does not check",
            "doesn't check",
        ],
        fix_keywords=["rowcount", "if cursor", "raise", "return", "check"],
        points=2.0,
    ),
    Bug(
        id="hard_none_due_date",
        line_number=80,
        bug_type="runtime_error",
        severity="major",
        description=(
            "task[6] (due_date) could be None or 'None' string for tasks added without a due_date. "
            "datetime.strptime will crash on None/invalid values. No null check."
        ),
        keywords=[
            "None",
            "null",
            "due_date",
            "strptime",
            "crash",
            "NoneType",
            "TypeError",
            "ValueError",
            "no check",
            "null check",
            "missing",
        ],
        fix_keywords=[
            "if task[6]",
            "is not None",
            "try",
            "except",
            "check",
            "guard",
        ],
        points=2.0,
    ),
    Bug(
        id="hard_export_no_error_handling",
        line_number=95,
        bug_type="error_handling",
        severity="minor",
        description=(
            "export_tasks has no error handling for file I/O operations. "
            "Could fail silently or crash on permission errors, disk full, etc."
        ),
        keywords=[
            "error handling",
            "no error",
            "exception",
            "try",
            "file",
            "I/O",
            "permission",
            "disk",
            "IOError",
            "OSError",
        ],
        fix_keywords=["try", "except", "IOError", "OSError", "finally"],
        points=1.0,
    ),
    Bug(
        id="hard_del_cleanup",
        line_number=100,
        bug_type="design",
        severity="minor",
        description=(
            "__del__ is unreliable for resource cleanup. Python does not guarantee "
            "when __del__ is called. Should implement __enter__/__exit__ (context manager) instead."
        ),
        keywords=[
            "__del__",
            "destructor",
            "unreliable",
            "context manager",
            "cleanup",
            "resource",
            "garbage collect",
            "__enter__",
            "__exit__",
            "with statement",
        ],
        fix_keywords=[
            "__enter__",
            "__exit__",
            "context manager",
            "with",
            "atexit",
            "close()",
        ],
        points=1.0,
    ),
]

HARD_TASK = Task(
    name="full_review",
    description=(
        "Perform a comprehensive code review of this TaskManager class.\n"
        "Find all bugs including security vulnerabilities, logic errors, "
        "missing error handling, and design issues.\n"
        "For each bug: state the line number, severity (critical/major/minor), "
        "describe the issue, and suggest a fix.\nThere are 6 bugs to find."
    ),
    difficulty="hard",
    filename="task_manager.py",
    language="python",
    code=HARD_CODE,
    bugs=HARD_BUGS,
    max_steps=10,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TASKS: Dict[str, Task] = {
    "single_bug": EASY_TASK,
    "multi_bug": MEDIUM_TASK,
    "full_review": HARD_TASK,
}


def get_task(name: str) -> Task:
    """Return a task by name or raise ValueError."""
    if name not in TASKS:
        raise ValueError(
            f"Unknown task '{name}'. Available: {list(TASKS.keys())}"
        )
    return TASKS[name]


def list_tasks() -> List[str]:
    """Return available task names."""
    return list(TASKS.keys())
