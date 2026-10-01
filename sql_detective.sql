-- ============================================================
-- Part 2 — SQL Detective Challenge
-- RecruiterFlow Backend Intern Assignment
-- ============================================================
-- Schema used (loaded as-is, not redesigned):
--   recruiters, job_postings, applicants, interviews
-- ============================================================


-- ------------------------------------------------------------
-- Q1: List all currently open job postings, along with the
--     name of the recruiter who owns each one.
-- ------------------------------------------------------------

SELECT
    jp.id          AS job_posting_id,
    jp.title,
    jp.department,
    jp.opened_date,
    r.name         AS recruiter_name,
    r.region
FROM   job_postings jp
JOIN   recruiters   r  ON r.id = jp.recruiter_id
WHERE  jp.status = 'open'
ORDER  BY jp.opened_date;


-- ------------------------------------------------------------
-- Q2: For each job posting, how many applicants reached the
--     Final interview stage?
-- ------------------------------------------------------------

SELECT
    jp.id    AS job_posting_id,
    jp.title,
    COUNT(i.id) AS final_stage_applicants
FROM   job_postings jp
LEFT   JOIN interviews i
       ON  i.job_posting_id = jp.id
       AND i.stage = 'Final'
GROUP  BY jp.id, jp.title
ORDER  BY jp.id;


-- ------------------------------------------------------------
-- Q3: Find every person who effectively applied to more than
--     one job posting. Careful — the data isn't as clean as it looks.
--
--     The data is messy: "Ananya Rao" appears twice with
--     different email capitalisation (ananya.rao@mail.com vs
--     Ananya.Rao@mail.com). We normalise email to lower-case
--     and group by (lower_email, lower_name) to deduplicate
--     the same person before checking cross-job activity.
--
--     Strategy:
--       1. Build a canonical identity: LOWER(email) as the key
--          (email is more reliable than name for dedup).
--       2. Collect all distinct job_posting_ids that identity
--          has an interview record for.
--       3. Return identities with > 1 distinct job posting.
-- ------------------------------------------------------------

WITH canonical_applicants AS (
    -- Collapse duplicate applicant rows for the same real person
    SELECT
        LOWER(email)     AS canonical_email,
        LOWER(full_name) AS canonical_name,
        id               AS applicant_id
    FROM applicants
),
applicant_jobs AS (
    -- For each canonical identity, collect distinct jobs they interviewed for
    SELECT
        ca.canonical_email,
        ca.canonical_name,
        COUNT(DISTINCT i.job_posting_id) AS distinct_jobs_applied
    FROM canonical_applicants ca
    JOIN interviews i ON i.applicant_id = ca.applicant_id
    GROUP BY ca.canonical_email, ca.canonical_name
)
SELECT
    canonical_name   AS applicant_name,
    canonical_email  AS email,
    distinct_jobs_applied
FROM   applicant_jobs
WHERE  distinct_jobs_applied > 1
ORDER  BY distinct_jobs_applied DESC, canonical_name;
