-- ============================================================
-- Recruiter Bot — Hand-written DDL
-- Database: SQLite
-- ============================================================

-- Skills normalised lookup table.
-- Storing skills as a separate table lets us do exact, indexed
-- matching without string-splitting at query time.
CREATE TABLE IF NOT EXISTS skills (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE
);

-- Candidates master table.
-- traits and quirk are stored as plain text; traits is a
-- comma-separated list we parse in Python so we stay on raw SQL.
-- availability is an enum-like text: 'immediate', '2_weeks', 'not_looking'.
CREATE TABLE IF NOT EXISTS candidates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    experience_years INTEGER NOT NULL,
    availability     TEXT    NOT NULL CHECK (availability IN ('immediate', '2_weeks', 'not_looking')),
    traits           TEXT    NOT NULL,  -- comma-separated, e.g. "analytical,blunt"
    quirk            TEXT
);

-- Many-to-many: which skills does each candidate have?
CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INTEGER NOT NULL REFERENCES skills(id)     ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

-- Jobs master table.
-- culture_keywords is comma-separated text, same reasoning as traits.
CREATE TABLE IF NOT EXISTS jobs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT    NOT NULL,
    min_experience     INTEGER NOT NULL,
    culture_keywords   TEXT    NOT NULL,  -- comma-separated
    tagline            TEXT
);

-- Many-to-many: which skills does each job require?
CREATE TABLE IF NOT EXISTS job_required_skills (
    job_id   INTEGER NOT NULL REFERENCES jobs(id)   ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- Pre-computed match cache.
-- Re-populated by POST /matches/compute.
-- breakdown stores JSON explaining each scoring component.
-- reason is a human-readable summary string.
CREATE TABLE IF NOT EXISTS matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_id       INTEGER NOT NULL REFERENCES jobs(id)       ON DELETE CASCADE,
    score        REAL    NOT NULL,
    breakdown    TEXT    NOT NULL,  -- JSON text
    reason       TEXT    NOT NULL,
    computed_at  TEXT    NOT NULL,  -- ISO-8601 timestamp
    UNIQUE (candidate_id, job_id)
);

-- Indexes to speed up match lookups (the two primary query patterns).
CREATE INDEX IF NOT EXISTS idx_matches_job       ON matches (job_id,       score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_candidate ON matches (candidate_id, score DESC);
