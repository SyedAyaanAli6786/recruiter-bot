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

The algorithm is intentionally transparent: every component is stored in the
`breakdown` JSON column so callers can explain the score to users.
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
    Compute the match score and return a rich result dict containing the
    numeric score, a per-component breakdown, and a human-readable reason string.
    """

    # --- 1. Skill overlap (50 pts) ---
    if job_skills:
        matched = candidate_skills & job_skills
        skill_score = round(len(matched) / len(job_skills) * 50, 2)
    else:
        matched = set()
        skill_score = 50.0  # job has no requirements -> full marks

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

    # --- 4. Trait / culture match (10 pts) ---
    candidate_traits = {t.strip().lower() for t in candidate["traits"].split(",") if t.strip()}
    culture_kw       = {k.strip().lower() for k in job["culture_keywords"].split(",") if k.strip()}
    trait_overlap    = candidate_traits & culture_kw
    max_possible     = max(len(culture_kw), 1)
    trait_score      = round(len(trait_overlap) / max_possible * 10, 2)

    total = round(skill_score + exp_score + avail_score + trait_score, 2)

    # --- Reason string ---
    matched_sorted = sorted(matched) if matched else []
    reason_parts = [
        f"Matched {len(matched)}/{len(job_skills)} required skill(s)"
        + (f" ({', '.join(matched_sorted)})" if matched_sorted else "") + ".",
        f"{candidate['experience_years']} yr(s) experience (min {job['min_experience']}) — {exp_label}.",
        f"Availability: {avail.replace('_', ' ')} ({avail_score}/10 pts).",
        f"Culture/trait overlap: {len(trait_overlap)}/{len(culture_kw)} keyword(s)"
        + (f" ({', '.join(sorted(trait_overlap))})" if trait_overlap else "") + ".",
    ]
    reason = " ".join(reason_parts)

    breakdown = {
        "skill_overlap":    {"score": skill_score,  "matched": sorted(matched),  "required": sorted(job_skills)},
        "experience_fit":   {"score": exp_score,     "candidate_yrs": candidate["experience_years"], "min_required": job["min_experience"], "note": exp_label},
        "availability":     {"score": avail_score,   "status": avail},
        "trait_culture":    {"score": trait_score,   "matched_keywords": sorted(trait_overlap), "culture_keywords": sorted(culture_kw)},
    }

    return {
        "candidate_id":  candidate["id"],
        "candidate_name": candidate["name"],
        "job_id":        job["id"],
        "job_title":     job["title"],
        "score":         total,
        "breakdown":     breakdown,
        "reason":        reason,
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def compute_all_matches() -> int:
    """
    Compute (or recompute) scores for every (candidate, job) pair and upsert
    into the matches table.  Returns the number of pairs processed.
    """
    candidates = _get_all_candidates()
    jobs       = _get_all_jobs()
    now        = datetime.now(timezone.utc).isoformat()
    count      = 0

    for candidate in candidates:
        c_skills = _get_candidate_skills(candidate["id"])
        for job in jobs:
            j_skills = _get_job_required_skills(job["id"])
            result   = _score(candidate, job, c_skills, j_skills)

            db.execute(
                """
                INSERT INTO matches (candidate_id, job_id, score, breakdown, reason, computed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (candidate_id, job_id)
                DO UPDATE SET
                    score       = excluded.score,
                    breakdown   = excluded.breakdown,
                    reason      = excluded.reason,
                    computed_at = excluded.computed_at
                """,
                (
                    result["candidate_id"],
                    result["job_id"],
                    result["score"],
                    json.dumps(result["breakdown"]),
                    result["reason"],
                    now,
                ),
            )
            count += 1

    return count


def get_matches_for_job(job_id: int) -> list[dict]:
    """
    Return candidates ranked for a given job, highest score first.
    Tie-break: alphabetical candidate name (ascending).
    """
    rows = db.fetchall(
        """
        SELECT
            m.score,
            m.breakdown,
            m.reason,
            m.computed_at,
            c.id   AS candidate_id,
            c.name AS candidate_name,
            c.experience_years,
            c.availability,
            c.traits
        FROM   matches m
        JOIN   candidates c ON c.id = m.candidate_id
        WHERE  m.job_id = ?
        ORDER  BY m.score DESC, c.name ASC
        """,
        (job_id,),
    )
    for r in rows:
        r["breakdown"] = json.loads(r["breakdown"])
    return rows


def get_matches_for_candidate(candidate_id: int) -> list[dict]:
    """
    Return jobs ranked for a given candidate, highest score first.
    Tie-break: alphabetical job title (ascending).
    """
    rows = db.fetchall(
        """
        SELECT
            m.score,
            m.breakdown,
            m.reason,
            m.computed_at,
            j.id      AS job_id,
            j.title   AS job_title,
            j.min_experience,
            j.culture_keywords,
            j.tagline
        FROM   matches m
        JOIN   jobs j ON j.id = m.job_id
        WHERE  m.candidate_id = ?
        ORDER  BY m.score DESC, j.title ASC
        """,
        (candidate_id,),
    )
    for r in rows:
        r["breakdown"] = json.loads(r["breakdown"])
    return rows
