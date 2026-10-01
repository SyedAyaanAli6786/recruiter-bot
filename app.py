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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
