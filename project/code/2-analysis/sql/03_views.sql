-- View compliance: setiap hasil ukur dipasangkan dengan revisi spec yang BERLAKU pada tanggal uji (ASOF JOIN), lalu dihitung putusan dan margin.
-- Putusan dihitung dengan aturan pasti (>= batas bawah, <= batas atas); LLM tidak ikut menentukan.
CREATE OR REPLACE VIEW param_sd AS
SELECT model, parameter, stddev_samp(value) AS sd FROM measurement GROUP BY model, parameter;

CREATE OR REPLACE VIEW compliance_result AS
WITH j AS (
    SELECT m.unit_id, m.model, m.parameter, m.test_date, m.value, s.revision, s.valid_from, s.lower_limit, s.upper_limit
    FROM measurement m
    ASOF LEFT JOIN dim_spec s ON m.model = s.model AND m.parameter = s.parameter AND m.test_date >= s.valid_from
), r AS (
    SELECT j.*, ps.sd,
           (lower_limit IS NULL OR value >= lower_limit) AND (upper_limit IS NULL OR value <= upper_limit) AS is_pass,
           LEAST(COALESCE(value - lower_limit, 1e18), COALESCE(upper_limit - value, 1e18)) AS margin_abs,
           CASE WHEN lower_limit IS NOT NULL AND (upper_limit IS NULL OR value - lower_limit <= upper_limit - value) THEN lower_limit ELSE upper_limit END AS nearest_limit
    FROM j JOIN param_sd ps USING (model, parameter)
)
SELECT unit_id, model, parameter, test_date, strftime(test_date, '%Y-%m') AS month, revision, lower_limit, upper_limit, value,
       margin_abs, margin_abs / abs(nearest_limit) AS margin_pct, margin_abs / sd AS margin_sd,
       CASE WHEN is_pass THEN 'pass' ELSE 'fail' END AS result
FROM r;

-- Putusan unit: lolos jika semua parameter yang tersedia lolos.
CREATE OR REPLACE VIEW unit_result AS
SELECT unit_id, any_value(model) AS model, min(test_date) AS test_date, strftime(min(test_date), '%Y-%m') AS month, count(*) AS n_params,
       bool_and(result = 'pass') AS unit_pass
FROM compliance_result GROUP BY unit_id;
