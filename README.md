# Recruiter Bot

A backend REST API that ingests candidate profiles and job openings, then ranks the best matches for each — built for the RecruiterFlow Backend Developer Intern assignment.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.10+ | Strong stdlib, minimal ceremony for a service this size |
| Web framework | Flask 3 | Thin, explicit routing, no magic |
| Database | SQLite | Zero-install, file-based, ships in Python stdlib — easy to run locally |
| SQL access | `sqlite3` module (raw, hand-written SQL) | Fulfils the "no ORM / no query builder" constraint |

---

## Project Structure

```
recruiter_bot/
├── app.py            # Flask app + all route handlers
├── db.py             # Raw SQLite connection & query helpers
├── schema.sql        # Hand-written DDL (CREATE TABLE statements)
├── seed.py           # Seed script (candidates + jobs) — idempotent
├── matcher.py        # Matching algorithm
├── requirements.txt
├── sql_detective.sql # Part 2 — SQL Detective queries
└── README.md
```

---

## How to Run Locally

**Prerequisites:** Python 3.10+

```bash
# 1. Navigate into the project folder
cd recruiter_bot

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies (just Flask)
pip install -r requirements.txt

# 4. Start the server
python app.py
# → Running on http://127.0.0.1:5000
```

The database schema is created automatically on first startup. No migrations needed.

---

## Seeding Data & Computing Matches

```bash
# Option A — via API (server must be running)
curl -X POST http://localhost:5000/seed
curl -X POST http://localhost:5000/matches/compute

# Option B — standalone script (no server needed)
python seed.py
python -c "import db, matcher; db.init_db(); matcher.compute_all_matches(); print('done')"
```

---

## API Reference

### Health

```bash
curl http://localhost:5000/
# {"status": "ok", "service": "recruiter-bot"}
```

### List all jobs

```bash
curl http://localhost:5000/jobs
```

### Get one job

```bash
curl http://localhost:5000/jobs/1
```

### Ranked candidates for a job ⭐

```bash
curl http://localhost:5000/jobs/1/matches
# Returns candidates ranked by score for job 1 ("Backend Detective")
# Includes score, per-component breakdown, and human-readable reason
```

Example response snippet:
```json
{
  "job_id": 1,
  "job_title": "Backend Detective",
  "matches": [
    {
      "candidate_id": 1,
      "candidate_name": "Sherlock H.",
      "score": 100.0,
      "reason": "Matched 3/3 required skill(s) (deduction, forensics, pattern-recognition). 8 yr(s) experience (min 3) — meets requirement. Availability: immediate (10/10 pts). Culture/trait overlap: 1/2 keyword(s) (analytical).",
      "breakdown": {
        "skill_overlap":  {"score": 50.0, "matched": ["deduction","forensics","pattern-recognition"], "required": ["deduction","forensics","pattern-recognition"]},
        "experience_fit": {"score": 30.0, "candidate_yrs": 8, "min_required": 3, "note": "meets requirement"},
        "availability":   {"score": 10.0, "status": "immediate"},
        "trait_culture":  {"score": 10.0, "matched_keywords": ["analytical"], "culture_keywords": ["analytical","autonomous"]}
      },
      "computed_at": "2026-10-01T..."
    },
    ...
  ]
}
```

### List all candidates

```bash
curl http://localhost:5000/candidates
```

### Get one candidate

```bash
curl http://localhost:5000/candidates/1
```

### Ranked jobs for a candidate ⭐

```bash
curl http://localhost:5000/candidates/1/matches
# Returns jobs ranked by score for candidate 1 (Sherlock H.)
```

### Seed data (idempotent)

```bash
curl -X POST http://localhost:5000/seed
```

### Recompute all match scores

```bash
curl -X POST http://localhost:5000/matches/compute
```

---

## Matching Algorithm

### Scoring (max 100 points)

| Component | Weight | Logic |
|-----------|--------|-------|
| **Skill overlap** | 50 pts | `|candidate_skills ∩ required_skills| / |required_skills| × 50` |
| **Experience fit** | 30 pts | ≥ min → 30; exactly 1 yr below → 15 (partial credit); otherwise → 0 |
| **Availability** | 10 pts | `immediate` → 10, `2_weeks` → 6, `not_looking` → 0 |
| **Trait / culture match** | 10 pts | `|candidate_traits ∩ culture_keywords| / |culture_keywords| × 10` |

### Design decisions & trade-offs

**Why skill overlap is the dominant signal (50 pts).**
A candidate who doesn't have the required skills is generally a non-starter, regardless of everything else. Giving it half the total score ensures a zero-skill-match candidate can never beat someone with full coverage, even if they ace every other dimension.

**Why experience fit has a "within 1 year" partial credit.**
A hard cliff at the minimum year threshold throws away candidates who are genuinely close. A junior who's one year short is more useful to surface than someone with five years but zero matching skills. The partial credit is intentionally modest (15/30) — it's a tiebreaker, not a pass.

**Why availability is included (10 pts).**
"Not looking" candidates are a real cost: they may need a longer courtship or may decline. Surfacing immediately-available candidates higher is useful for a recruiter under time pressure. Weighting it at 10 pts means it can't override a strong skill match but it does meaningfully separate peers.

**Why trait/culture match is last (10 pts).**
Culture fit signals are soft and ambiguous — "analytical" might describe dozens of people. It's a useful tiebreaker but shouldn't override hard requirements. 10 pts is enough to separate equal-skill candidates without letting a buzzword override substance.

**Pre-computed match cache.**
All `(candidate, job)` pairs are scored once and stored in the `matches` table. `GET /jobs/{id}/matches` and `GET /candidates/{id}/matches` are then simple indexed lookups. The trade-off: data is stale until `POST /matches/compute` is re-run. For a service at this scale that's fine; at production scale you'd hook compute into the candidate/job write path or run it on a schedule.

**Tie-breaking.**
Equal-score pairs are broken alphabetically by name. This is purely deterministic — there's no semantic reason to prefer one over another in a true tie.

---

## Part 2 — SQL Detective

The five queries are in [`sql_detective.sql`](sql_detective.sql).

The most interesting case is **Q3** (applicants who applied to multiple jobs): the `applicants` table has "Ananya Rao" appear twice with different email capitalisation (`ananya.rao@mail.com` vs `Ananya.Rao@mail.com`). The query normalises both `email` and `name` to lowercase before grouping, treating them as the same person and correctly counting their combined job-posting activity.

---

## AI Tool Usage

Antigravity (Google DeepMind's agentic coding assistant, similar to GitHub Copilot) was used to generate the full implementation from a detailed plan that was reviewed and approved before execution. Every design decision — the scoring weights, the partial-credit logic, the schema normalisation, the SQL detective approach — was planned explicitly upfront. The code was then generated to match that plan. I understand every line and can walk through any of it in the follow-up conversation.
