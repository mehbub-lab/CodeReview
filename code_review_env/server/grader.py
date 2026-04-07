"""
Deterministic grader for the Code Review Environment.

Scores agent messages by matching line numbers, bug-type keywords,
and fix-suggestion keywords against the known bug database.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from code_review_env.server.tasks import Bug


@dataclass
class BugMatch:
    """Result of matching an agent message against a single bug."""

    bug_id: str
    line_matched: bool = False
    keywords_matched: int = 0
    fix_matched: bool = False
    score: float = 0.0


@dataclass
class GradeResult:
    """Result of grading a single step's message."""

    step_reward: float = 0.0
    new_bugs_found: List[str] = field(default_factory=list)
    feedback: str = ""
    details: Dict[str, BugMatch] = field(default_factory=dict)


# ----- helpers -----

_LINE_PATTERNS = [
    re.compile(r"line\s+(\d+)", re.IGNORECASE),
    re.compile(r"L(\d+)", re.IGNORECASE),
    re.compile(r"#\s*(\d+)"),
    re.compile(r"at\s+(\d+)", re.IGNORECASE),
    re.compile(r"on\s+line\s+(\d+)", re.IGNORECASE),
    re.compile(r"row\s+(\d+)", re.IGNORECASE),
    re.compile(r":(\d+)"),  # filename:lineno style
]

LINE_TOLERANCE = 3  # ±3 lines


def _extract_line_numbers(text: str) -> Set[int]:
    """Extract all line numbers mentioned in the text."""
    numbers: Set[int] = set()
    for pat in _LINE_PATTERNS:
        for m in pat.finditer(text):
            try:
                numbers.add(int(m.group(1)))
            except (ValueError, IndexError):
                pass
    return numbers


def _keyword_match(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def grade_message(
    message: str,
    bugs: List[Bug],
    already_found: Set[str],
) -> GradeResult:
    """
    Grade an agent's review message against the known bugs.

    Scoring per bug (only for newly found bugs):
      - Line number match (±tolerance):  40 % of bug points
      - Bug-type keyword match:          40 % of bug points
      - Fix suggestion keyword match:    20 % of bug points

    Returns a GradeResult with reward, newly found bug IDs, and feedback.
    """
    mentioned_lines = _extract_line_numbers(message)
    result = GradeResult()

    for bug in bugs:
        if bug.id in already_found:
            continue

        bm = BugMatch(bug_id=bug.id)

        # --- line match ---
        for ln in mentioned_lines:
            if abs(ln - bug.line_number) <= LINE_TOLERANCE:
                bm.line_matched = True
                break

        # --- keyword match ---
        bm.keywords_matched = _keyword_match(message, bug.keywords)

        # --- fix match ---
        fix_count = _keyword_match(message, bug.fix_keywords)
        bm.fix_matched = fix_count > 0

        # --- compute score ---
        if bm.line_matched and bm.keywords_matched > 0:
            # Bug is considered "found"
            line_score = 0.4 * bug.points
            kw_frac = min(bm.keywords_matched / max(len(bug.keywords) * 0.3, 1), 1.0)
            kw_score = 0.4 * bug.points * kw_frac
            fix_score = 0.2 * bug.points if bm.fix_matched else 0.0
            bm.score = line_score + kw_score + fix_score
            result.new_bugs_found.append(bug.id)
        elif bm.keywords_matched >= 2 and not bm.line_matched:
            # Partial credit: identified the type but wrong/missing line
            kw_frac = min(bm.keywords_matched / max(len(bug.keywords) * 0.3, 1), 1.0)
            bm.score = 0.25 * bug.points * kw_frac
            result.new_bugs_found.append(bug.id)
        # else: bug not detected

        result.details[bug.id] = bm
        result.step_reward += bm.score

    # --- generate feedback ---
    if result.new_bugs_found:
        names = ", ".join(result.new_bugs_found)
        result.feedback = (
            f"Good work! You identified {len(result.new_bugs_found)} new bug(s): "
            f"{names}. Reward: +{result.step_reward:.2f}"
        )
    else:
        result.feedback = (
            "No new bugs identified in this message. "
            "Try mentioning specific line numbers and describing the issue."
        )

    return result
