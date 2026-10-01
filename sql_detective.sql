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


-- ------------------------------------------------------------
-- Q4: For each recruiter, compute their Final-stage conversion
--     rate (passed / total Final-stage interviews), but only
--     include recruiters with at least 3 Final-stage interviews.
-- ------------------------------------------------------------

SELECT
    r.id             AS recruiter_id,
    r.name           AS recruiter_name,
    r.region,
    COUNT(i.id)                                          AS total_final_interviews,
    SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS passed_finals,
    ROUND(
        1.0 * SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END)
            / COUNT(i.id),
        4
    )                                                    AS conversion_rate
FROM   recruiters   r
JOIN   job_postings jp ON jp.recruiter_id = r.id
JOIN   interviews   i  ON i.job_posting_id = jp.id
                      AND i.stage = 'Final'
GROUP  BY r.id, r.name, r.region
HAVING COUNT(i.id) >= 3
ORDER  BY conversion_rate DESC;


-- ------------------------------------------------------------
-- Q5 (Bonus): Using a window function, find the recruiter with
--     the most successful placements (passed at Final stage)
--     per department.
--
--     "Most successful" = highest count of passed Final-stage
--     interviews within each department.
--     RANK() is used so ties both appear (RANK 1 = winner(s)).
-- ------------------------------------------------------------

WITH placements AS (
    -- Count passed-Final interviews per recruiter x department
    SELECT
        r.id             AS recruiter_id,
        r.name           AS recruiter_name,
        jp.department,
        COUNT(i.id)      AS passed_placements
    FROM   recruiters   r
    JOIN   job_postings jp ON jp.recruiter_id = r.id
    JOIN   interviews   i  ON i.job_posting_id = jp.id
                          AND i.stage   = 'Final'
                          AND i.outcome = 'passed'
    GROUP  BY r.id, r.name, jp.department
),
ranked AS (
    SELECT
        department,
        recruiter_id,
        recruiter_name,
        passed_placements,
        RANK() OVER (
            PARTITION BY department
            ORDER BY passed_placements DESC
        ) AS dept_rank
    FROM placements
)
SELECT
    department,
    recruiter_name,
    passed_placements,
    dept_rank
FROM   ranked
WHERE  dept_rank = 1
ORDER  BY department, recruiter_name;
