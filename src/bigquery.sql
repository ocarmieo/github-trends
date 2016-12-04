-- Extract package imports from Python files
-- Saved in table named "file_packages"
SELECT
  repo_name,
  file_path,
  id AS file_id,
  NEST(UNIQUE(COALESCE( # NEST aggregation creates repeated field column of matched packages
        REGEXP_EXTRACT(line, r"^from \.*(\w+)[\w.]* import"), REGEXP_EXTRACT(line, r"^import \.*(\w+)[\w.]*") ))) AS packages
FROM ( SELECT # filter lines that contain import
    id,
    sample_repo_name AS repo_name,
    sample_path AS file_path,
    LTRIM(SPLIT(content, "\n")) AS line
  FROM
    [fh-bigquery:github_extracts.contents_py]
  HAVING
    line CONTAINS "import")
GROUP BY
  repo_name,
  file_path,
  file_id
HAVING
  LENGTH(packages) > 0;

-- Select commit event data for Python files
-- Saved in table named "commits_py_diffpath"
SELECT
  commit,
  author.name,
  author.email,
  author.time_sec,
  author.tz_offset,
  author.date,
  committer.name,
  committer.email,
  committer.time_sec,
  committer.tz_offset,
  committer.date,
  subject,
  message,
  difference.new_path,
  repo_name
FROM
  FLATTEN([bigquery-public-data:github_repos.commits], repo_name)
WHERE
  RIGHT(difference.new_path, 3) = '.py';

-- Join code content with commit events
-- Saved in table named "commit_content_py"
SELECT
  commits.commit,
  commits.author.name,
  commits.author.email,
  commits.author.time_sec,
  commits.author.tz_offset,
  commits.author.date,
  commits.committer.name,
  commits.committer.email,
  commits.committer.time_sec,
  commits.committer.tz_offset,
  commits.committer.date,
  commits.subject,
  commits.message,
  commits.repo_name,
  contents.file_path,
  contents.file_id,
  contents.packages
FROM
  FLATTEN([singular-range-148905:github_trends.commits_py_diffpath], difference.new_path) AS commits
JOIN
  [singular-range-148905:github_trends.file_packages] AS contents
ON
  commits.difference.new_path = contents.file_path
  AND commits.repo_name = contents.repo_name;

-- Group package count by date
SELECT
  packages,
  min_author_date,
  COUNT(*) AS file_count
FROM
  (SELECT
    packages,
    file_id,
    MIN(DATE(author.date)) AS min_author_date
  FROM
    FLATTEN([singular-range-148905:github_trends.commit_content_py], packages)
  GROUP BY
    packages,
    file_id)
GROUP BY
  packages,
  min_author_date;