"""
app.py — Flask REST API for Recruiter Bot.

Endpoints (planned):
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

from flask import Flask, jsonify
import db

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
