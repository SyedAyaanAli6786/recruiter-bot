"""
matcher.py — Core matching algorithm.

Scoring breakdown (max 100 points):

  Component              Weight  Notes
  ---------------------  ------  -------------------------------------------
  Skill overlap          50 pts  matched_skills / required_skills x 50
  Experience fit         30 pts  >= min -> 30; within 1 yr below -> 15; else 0
  Availability           10 pts  immediate -> 10; 2_weeks -> 6; not_looking -> 0
  Trait / culture match  10 pts  |traits n culture_kw| / max_possible x 10

Tie-breaking: alphabetical by candidate name (deterministic).
"""

import json
from datetime import datetime, timezone
import db

# --------------------------------------------------------------------------- #
# Availability score map
# --------------------------------------------------------------------------- #
_AVAILABILITY_SCORE = {
    "immediate":   10,
    "2_weeks":      6,
    "not_looking":  0,
}

# --------------------------------------------------------------------------- #
# Low-level data fetchers (raw SQL)
# --------------------------------------------------------------------------- #

def _get_all_candidates() -> list[dict]:
    return db.fetchall("SELECT id, name, experience_years, availability, traits FROM candidates ORDER BY name")


def _get_all_jobs() -> list[dict]:
    return db.fetchall("SELECT id, title, min_experience, culture_keywords FROM jobs ORDER BY id")


def _get_candidate_skills(candidate_id: int) -> set[str]:
    rows = db.fetchall(
        """
        SELECT s.name
        FROM   candidate_skills cs
        JOIN   skills s ON s.id = cs.skill_id
        WHERE  cs.candidate_id = ?
        """,
        (candidate_id,),
    )
    return {r["name"] for r in rows}


def _get_job_required_skills(job_id: int) -> set[str]:
    rows = db.fetchall(
        """
        SELECT s.name
        FROM   job_required_skills jrs
        JOIN   skills s ON s.id = jrs.skill_id
        WHERE  jrs.job_id = ?
        """,
        (job_id,),
    )
    return {r["name"] for r in rows}


# --------------------------------------------------------------------------- #
# Core scoring function
# --------------------------------------------------------------------------- #

def _score(candidate: dict, job: dict, candidate_skills: set[str], job_skills: set[str]) -> dict:
    """
    Compute the match score and return a result dict.
    """

    # --- 1. Skill overlap (50 pts) ---
    if job_skills:
        matched = candidate_skills & job_skills
        skill_score = round(len(matched) / len(job_skills) * 50, 2)
    else:
        matched = set()
        skill_score = 50.0

    # --- 2. Experience fit (30 pts) ---
    exp_gap = candidate["experience_years"] - job["min_experience"]
    if exp_gap >= 0:
        exp_score = 30.0
        exp_label = "meets requirement"
    elif exp_gap == -1:
        exp_score = 15.0
        exp_label = "1 year below minimum (partial credit)"
    else:
        exp_score = 0.0
        exp_label = f"{abs(exp_gap)} years below minimum"

    # --- 3. Availability (10 pts) ---
    avail = candidate.get("availability", "not_looking")
    avail_score = _AVAILABILITY_SCORE.get(avail, 0)

    total = round(skill_score + exp_score + avail_score, 2)

    reason = (
        f"Matched {len(matched)}/{len(job_skills)} required skill(s). "
        f"{candidate['experience_years']} yr(s) experience (min {job['min_experience']}) — {exp_label}. "
        f"Availability: {avail.replace('_', ' ')} ({avail_score}/10 pts)."
    )

    breakdown = {
        "skill_overlap":  {"score": skill_score, "matched": sorted(matched), "required": sorted(job_skills)},
        "experience_fit": {"score": exp_score, "candidate_yrs": candidate["experience_years"],
                            "min_required": job["min_experience"], "note": exp_label},
        "availability":   {"score": avail_score, "status": avail},
    }

    return {
        "candidate_id":   candidate["id"],
        "candidate_name": candidate["name"],
        "job_id":         job["id"],
        "job_title":      job["title"],
        "score":          total,
        "breakdown":      breakdown,
        "reason":         reason,
    }
