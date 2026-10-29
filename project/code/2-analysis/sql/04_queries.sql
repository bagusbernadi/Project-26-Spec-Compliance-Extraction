-- Query analisis. Format: "-- name: <nama>" memulai satu query; hasilnya ditulis ke results/2-analysis/<nama>.csv oleh 07_run_queries.py.
-- Placeholder {NEAR} diganti nilai ambang hampir gagal (simpangan baku), {REV} diganti nomor revisi tetap.

-- name: passrate_param_model
SELECT parameter, model, count(*) AS n, sum((result = 'pass')::INT) AS n_pass, sum((result = 'fail')::INT) AS n_fail,
       avg((result = 'pass')::INT) AS pass_rate
FROM compliance_result GROUP BY parameter, model ORDER BY parameter, model;

-- name: passrate_param
SELECT parameter, count(*) AS n, sum((result = 'pass')::INT) AS n_pass, sum((result = 'fail')::INT) AS n_fail, avg((result = 'pass')::INT) AS pass_rate
FROM compliance_result GROUP BY parameter ORDER BY parameter;

-- name: passrate_unit
SELECT model, count(*) AS n, sum(unit_pass::INT) AS n_pass, avg(unit_pass::INT) AS pass_rate FROM unit_result GROUP BY model
UNION ALL
SELECT 'Semua', count(*), sum(unit_pass::INT), avg(unit_pass::INT) FROM unit_result ORDER BY model;

-- name: pareto_fail
WITH f AS (SELECT parameter, model, count(*) AS n_fail FROM compliance_result WHERE result = 'fail' GROUP BY parameter, model),
     t AS (SELECT sum(n_fail) AS tot FROM f)
SELECT parameter, model, n_fail, n_fail / tot AS share FROM f, t ORDER BY n_fail DESC, parameter, model;

-- name: fail_units_by_param
WITH fu AS (SELECT unit_id, list(parameter ORDER BY parameter) AS params, count(*) AS n_fail_params FROM compliance_result WHERE result = 'fail' GROUP BY unit_id)
SELECT n_fail_params, count(*) AS n_units FROM fu GROUP BY n_fail_params ORDER BY n_fail_params;

-- name: margin_param_model
SELECT parameter, model, count(*) AS n, median(margin_sd) AS median_margin_sd, quantile_cont(margin_sd, 0.05) AS p05_margin_sd, min(margin_sd) AS min_margin_sd,
       median(margin_pct) AS median_margin_pct, quantile_cont(margin_pct, 0.05) AS p05_margin_pct,
       sum((result = 'pass' AND margin_sd < {NEAR})::INT) AS n_near_fail, avg((result = 'pass' AND margin_sd < {NEAR})::INT) AS share_near_fail,
       avg((result = 'pass')::INT) AS pass_rate
FROM compliance_result GROUP BY parameter, model ORDER BY median_margin_sd;

-- name: margin_distribution
SELECT parameter, model, floor(margin_sd * 2) / 2 AS margin_bin_sd, count(*) AS n
FROM compliance_result WHERE margin_sd IS NOT NULL AND margin_sd < 8 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

-- name: month_param
SELECT month, parameter, count(*) AS n, sum((result = 'pass')::INT) AS n_pass, avg((result = 'pass')::INT) AS pass_rate
FROM compliance_result GROUP BY month, parameter ORDER BY month, parameter;

-- name: month_unit
SELECT month, count(*) AS n, sum(unit_pass::INT) AS n_pass, avg(unit_pass::INT) AS pass_rate FROM unit_result GROUP BY month ORDER BY month;

-- name: revision_param_model
SELECT model, parameter, revision, count(*) AS n, sum((result = 'pass')::INT) AS n_pass, avg((result = 'pass')::INT) AS pass_rate
FROM compliance_result GROUP BY model, parameter, revision ORDER BY model, parameter, revision;

-- name: wrong_revision_{REV}
SELECT c.parameter, c.model, count(*) AS n, sum((c.result = 'pass' AND f.is_pass)::INT) AS same_pass, sum((c.result = 'fail' AND NOT f.is_pass)::INT) AS same_fail,
       sum((c.result = 'fail' AND f.is_pass)::INT) AS false_pass, sum((c.result = 'pass' AND NOT f.is_pass)::INT) AS false_fail,
       sum((c.result = 'pass')::INT) AS n_pass_correct, sum(f.is_pass::INT) AS n_pass_with_wrong
FROM compliance_result c
JOIN (SELECT m.unit_id, m.parameter, (s.lower_limit IS NULL OR m.value >= s.lower_limit) AND (s.upper_limit IS NULL OR m.value <= s.upper_limit) AS is_pass
      FROM measurement m JOIN dim_spec s ON m.model = s.model AND m.parameter = s.parameter AND s.revision = '{REV}') f USING (unit_id, parameter)
GROUP BY c.parameter, c.model ORDER BY c.parameter, c.model;
