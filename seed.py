"""
seed.py — Load all candidate and job seed data into the database.

Can be run as a standalone script:
    python seed.py

Also called by the POST /seed API endpoint (idempotent).
Raw SQL only — no ORM.
"""

import db

# --------------------------------------------------------------------------- #
# Seed data — Candidates
# --------------------------------------------------------------------------- #

CANDIDATES = [
    {
        "name": "Sherlock H.",
        "skills": ["deduction", "pattern-recognition", "forensics"],
        "experience_years": 8,
        "availability": "immediate",
        "traits": "analytical,blunt",
        "quirk": "Solves problems by eliminating the impossible; occasionally insufferable in standups.",
    },
    {
        "name": "Hermione G.",
        "skills": ["research", "time-management", "public-speaking"],
        "experience_years": 4,
        "availability": "2_weeks",
        "traits": "detail-oriented,overachiever",
        "quirk": "Reads the entire documentation before writing a single line of code.",
    },
    {
        "name": "Tony S.",
        "skills": ["systems-design", "rapid-prototyping", "leadership"],
        "experience_years": 12,
        "availability": "not_looking",
        "traits": "confident,innovative",
        "quirk": "Ships an MVP overnight, refuses to write tests.",
    },
    {
        "name": "Leslie K.",
        "skills": ["project-management", "stakeholder-management", "public-speaking"],
        "experience_years": 6,
        "availability": "immediate",
        "traits": "tenacious,organized",
        "quirk": "Has a binder for everything, including the binder.",
    },
    {
        "name": "Ron S.",
        "skills": ["woodworking", "minimalism", "negotiation"],
        "experience_years": 15,
        "availability": "not_looking",
        "traits": "stubborn,principled",
        "quirk": "Refuses to use more than one monitor.",
    },
    {
        "name": "Rick S.",
        "skills": ["systems-design", "rapid-prototyping", "chemistry"],
        "experience_years": 20,
        "availability": "immediate",
        "traits": "genius,reckless",
        "quirk": "Solution works, mechanism deeply concerning.",
    },
    {
        "name": "Elle W.",
        "skills": ["persuasion", "research", "public-speaking"],
        "experience_years": 3,
        "availability": "immediate",
        "traits": "optimistic,sharp",
        "quirk": "Underestimated in every standup, correct in every retro.",
    },
    {
        "name": "MacGyver",
        "skills": ["rapid-prototyping", "resourcefulness", "chemistry", "systems-design"],
        "experience_years": 10,
        "availability": "2_weeks",
        "traits": "calm,improviser",
        "quirk": "Fixes production outages with duct tape and a paperclip metaphor.",
    },
    {
        "name": "Sheldon C.",
        "skills": ["theoretical-analysis", "pattern-recognition", "research"],
        "experience_years": 9,
        "availability": "immediate",
        "traits": "rigid,brilliant",
        "quirk": "Correct 95% of the time, insufferable 100% of the time.",
    },
    {
        "name": "Katniss E.",
        "skills": ["precision", "strategy", "crisis-management"],
        "experience_years": 5,
        "availability": "immediate",
        "traits": "resilient,decisive",
        "quirk": "Excellent under pressure, terrible with public speaking.",
    },
    {
        "name": "Michael S.",
        "skills": ["sales", "public-speaking", "team-building"],
        "experience_years": 11,
        "availability": "not_looking",
        "traits": "enthusiastic,chaotic",
        "quirk": "World's best boss, according to a mug he bought himself.",
    },
    {
        "name": "Olivia P.",
        "skills": ["crisis-management", "negotiation", "strategy", "leadership"],
        "experience_years": 13,
        "availability": "2_weeks",
        "traits": "decisive,intense",
        "quirk": "Handles it. Whatever it is.",
    },
    {
        "name": "Ted L.",
        "skills": ["team-building", "optimism", "mentorship", "public-speaking"],
        "experience_years": 7,
        "availability": "immediate",
        "traits": "empathetic,persistent",
        "quirk": "Turns every technical setback into a folksy metaphor.",
    },
    {
        "name": "Miranda P.",
        "skills": ["leadership", "negotiation", "stakeholder-management", "precision"],
        "experience_years": 18,
        "availability": "not_looking",
        "traits": "demanding,decisive",
        "quirk": "Reviews every PR personally. Says nothing. Everyone panics.",
    },
    {
        "name": "Dwight S.",
        "skills": ["sales", "negotiation", "security", "loyalty"],
        "experience_years": 9,
        "availability": "immediate",
        "traits": "intense,loyal",
        "quirk": "Assistant to the regional backend engineer.",
    },
]

# --------------------------------------------------------------------------- #
# Seed data — Jobs
# --------------------------------------------------------------------------- #

JOBS = [
    {
        "title": "Backend Detective",
        "required_skills": ["deduction", "pattern-recognition", "forensics"],
        "min_experience": 3,
        "culture_keywords": "analytical,autonomous",
        "tagline": "We have a bug. We have no leads. We have you.",
    },
    {
        "title": "Rapid Prototyping Engineer",
        "required_skills": ["rapid-prototyping", "systems-design"],
        "min_experience": 2,
        "culture_keywords": "innovative,fast-paced",
        "tagline": "Ship first, document never (kidding — please document).",
    },
    {
        "title": "Developer Relations Lead",
        "required_skills": ["public-speaking", "research"],
        "min_experience": 2,
        "culture_keywords": "energetic,curious",
        "tagline": "Explain complex things to confused humans, cheerfully.",
    },
    {
        "title": "Engineering Manager, Chaos Team",
        "required_skills": ["team-building", "stakeholder-management", "leadership"],
        "min_experience": 5,
        "culture_keywords": "empathetic,organized",
        "tagline": "Herd cats. The cats are senior engineers.",
    },
    {
        "title": "Incident Commander",
        "required_skills": ["crisis-management", "strategy", "negotiation"],
        "min_experience": 4,
        "culture_keywords": "decisive,calm-under-pressure",
        "tagline": "3am page. You're the one who picks up.",
    },
    {
        "title": "Sales Engineer",
        "required_skills": ["sales", "public-speaking", "negotiation"],
        "min_experience": 3,
        "culture_keywords": "enthusiastic,persistent",
        "tagline": "Sell the vision, then go build it.",
    },
]


# --------------------------------------------------------------------------- #
# Insertion helpers — raw SQL
# --------------------------------------------------------------------------- #

def _upsert_skill(conn, name: str) -> int:
    """Insert skill if not exists; return its id."""
    conn.execute(
        "INSERT OR IGNORE INTO skills (name) VALUES (?)",
        (name,),
    )
    row = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
    return row[0]


def _candidate_exists(conn, name: str) -> bool:
    row = conn.execute("SELECT id FROM candidates WHERE name = ?", (name,)).fetchone()
    return row is not None


def _job_exists(conn, title: str) -> bool:
    row = conn.execute("SELECT id FROM jobs WHERE title = ?", (title,)).fetchone()
    return row is not None


def run_seed() -> dict:
    """
    Load all seed data idempotently (skips rows that already exist by name/title).
    Returns counts of inserted candidates and jobs.
    """
    import sqlite3

    conn = sqlite3.connect(db.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    inserted_candidates = 0
    inserted_jobs = 0

    try:
        # ---- Candidates ----
        for c in CANDIDATES:
            if _candidate_exists(conn, c["name"]):
                continue  # idempotent — skip

            cur = conn.execute(
                """
                INSERT INTO candidates (name, experience_years, availability, traits, quirk)
                VALUES (?, ?, ?, ?, ?)
                """,
                (c["name"], c["experience_years"], c["availability"], c["traits"], c.get("quirk", "")),
            )
            candidate_id = cur.lastrowid

            for skill_name in c["skills"]:
                skill_id = _upsert_skill(conn, skill_name)
                conn.execute(
                    "INSERT OR IGNORE INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
                    (candidate_id, skill_id),
                )

            inserted_candidates += 1

        # ---- Jobs ----
        for j in JOBS:
            if _job_exists(conn, j["title"]):
                continue  # idempotent — skip

            cur = conn.execute(
                """
                INSERT INTO jobs (title, min_experience, culture_keywords, tagline)
                VALUES (?, ?, ?, ?)
                """,
                (j["title"], j["min_experience"], j["culture_keywords"], j.get("tagline", "")),
            )
            job_id = cur.lastrowid

            for skill_name in j["required_skills"]:
                skill_id = _upsert_skill(conn, skill_name)
                conn.execute(
                    "INSERT OR IGNORE INTO job_required_skills (job_id, skill_id) VALUES (?, ?)",
                    (job_id, skill_id),
                )

            inserted_jobs += 1

        conn.commit()

    finally:
        conn.close()

    return {"inserted_candidates": inserted_candidates, "inserted_jobs": inserted_jobs}


if __name__ == "__main__":
    db.init_db()
    result = run_seed()
    print(f"Seed complete: {result['inserted_candidates']} candidate(s), {result['inserted_jobs']} job(s) inserted.")
