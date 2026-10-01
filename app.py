"""
app.py — Flask REST API for Recruiter Bot.

Endpoints:
  GET  /                         Health check
  GET  /candidates               List all candidates
  GET  /candidates/<id>          Get one candidate
  GET  /candidates/<id>/matches  Ranked jobs for a candidate
  GET  /jobs                     List all jobs
  GET  /jobs/<id>                Get one job
  GET  /jobs/<id>/matches        Ranked candidates for a job
  POST /seed                     Load seed data (idempotent)
  POST /matches/compute          (Re-)compute all match scores

Raw SQL only — no ORM.
"""

from flask import Flask, jsonify, abort
import db
import matcher
import seed as seed_module

app = Flask(__name__)


# --------------------------------------------------------------------------- #
# Startup: ensure schema exists
# --------------------------------------------------------------------------- #

with app.app_context():
    db.init_db()


# --------------------------------------------------------------------------- #
# Health check
# --------------------------------------------------------------------------- #

@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "recruiter-bot"})


# --------------------------------------------------------------------------- #
# Candidates
# --------------------------------------------------------------------------- #

@app.get("/candidates")
def list_candidates():
    """List all candidates with their skills."""
    candidates = db.fetchall(
        """
        SELECT id, name, experience_years, availability, traits, quirk
        FROM   candidates
        ORDER  BY name
        """
    )
    # Attach skill list to each candidate via a raw JOIN query
    for c in candidates:
        skills = db.fetchall(
            """
            SELECT s.name
            FROM   candidate_skills cs
            JOIN   skills s ON s.id = cs.skill_id
            WHERE  cs.candidate_id = ?
            ORDER  BY s.name
            """,
            (c["id"],),
        )
        c["skills"] = [s["name"] for s in skills]
    return jsonify(candidates)


@app.get("/candidates/<int:candidate_id>")
def get_candidate(candidate_id: int):
    """Get a single candidate by id."""
    c = db.fetchone(
        "SELECT id, name, experience_years, availability, traits, quirk FROM candidates WHERE id = ?",
        (candidate_id,),
    )
    if not c:
        abort(404, description=f"Candidate {candidate_id} not found.")
    skills = db.fetchall(
        """
        SELECT s.name
        FROM   candidate_skills cs
        JOIN   skills s ON s.id = cs.skill_id
        WHERE  cs.candidate_id = ?
        ORDER  BY s.name
        """,
        (candidate_id,),
    )
    c["skills"] = [s["name"] for s in skills]
    return jsonify(c)


@app.get("/candidates/<int:candidate_id>/matches")
def candidate_matches(candidate_id: int):
    """
    Return all jobs ranked for a candidate (highest score first).
    Run POST /matches/compute first if the matches table is empty.
    """
    # Verify candidate exists
    if not db.fetchone("SELECT id FROM candidates WHERE id = ?", (candidate_id,)):
        abort(404, description=f"Candidate {candidate_id} not found.")

    results = matcher.get_matches_for_candidate(candidate_id)
    if not results:
        return jsonify({
            "message": "No match data found. Run POST /matches/compute first.",
            "candidate_id": candidate_id,
            "matches": [],
        }), 200

    c = db.fetchone("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
    return jsonify({
        "candidate_id": candidate_id,
        "candidate_name": c["name"] if c else None,
        "matches": results,
    })


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #

@app.get("/jobs")
def list_jobs():
    """List all jobs with their required skills."""
    jobs = db.fetchall(
        "SELECT id, title, min_experience, culture_keywords, tagline FROM jobs ORDER BY id"
    )
    for j in jobs:
        skills = db.fetchall(
            """
            SELECT s.name
            FROM   job_required_skills jrs
            JOIN   skills s ON s.id = jrs.skill_id
            WHERE  jrs.job_id = ?
            ORDER  BY s.name
            """,
            (j["id"],),
        )
        j["required_skills"] = [s["name"] for s in skills]
    return jsonify(jobs)


@app.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    """Get a single job by id."""
    j = db.fetchone(
        "SELECT id, title, min_experience, culture_keywords, tagline FROM jobs WHERE id = ?",
        (job_id,),
    )
    if not j:
        abort(404, description=f"Job {job_id} not found.")
    skills = db.fetchall(
        """
        SELECT s.name
        FROM   job_required_skills jrs
        JOIN   skills s ON s.id = jrs.skill_id
        WHERE  jrs.job_id = ?
        ORDER  BY s.name
        """,
        (job_id,),
    )
    j["required_skills"] = [s["name"] for s in skills]
    return jsonify(j)


@app.get("/jobs/<int:job_id>/matches")
def job_matches(job_id: int):
    """
    Return all candidates ranked for a job (highest score first).
    Run POST /matches/compute first if the matches table is empty.
    """
    if not db.fetchone("SELECT id FROM jobs WHERE id = ?", (job_id,)):
        abort(404, description=f"Job {job_id} not found.")

    results = matcher.get_matches_for_job(job_id)
    if not results:
        return jsonify({
            "message": "No match data found. Run POST /matches/compute first.",
            "job_id": job_id,
            "matches": [],
        }), 200

    j = db.fetchone("SELECT title FROM jobs WHERE id = ?", (job_id,))
    return jsonify({
        "job_id": job_id,
        "job_title": j["title"] if j else None,
        "matches": results,
    })


# --------------------------------------------------------------------------- #
# Seed + compute
# --------------------------------------------------------------------------- #

@app.post("/seed")
def seed():
    """Load all seed data (idempotent — safe to call multiple times)."""
    result = seed_module.run_seed()
    return jsonify({
        "status": "ok",
        "inserted_candidates": result["inserted_candidates"],
        "inserted_jobs": result["inserted_jobs"],
        "message": "Seed complete. Run POST /matches/compute to score matches.",
    })


@app.post("/matches/compute")
def compute_matches():
    """(Re-)compute all match scores for every (candidate, job) pair."""
    count = matcher.compute_all_matches()
    return jsonify({
        "status": "ok",
        "pairs_computed": count,
        "message": f"Computed {count} match pair(s). Scores are now queryable.",
    })


# --------------------------------------------------------------------------- #
# Error handlers
# --------------------------------------------------------------------------- #

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e)}), 404


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
