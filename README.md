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
