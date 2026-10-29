-- Memuat CSV hasil langkah sebelumnya (path relatif terhadap folder project/).
INSERT INTO dim_spec
SELECT model, revision, CAST(valid_from AS DATE), parameter, lower_limit, upper_limit, COALESCE(unit, ''), source_doc, source_page, n_docs_agree, n_docs
FROM read_csv('results/1-data-preparation/dim_spec.csv', header = true, nullstr = '', all_varchar = false, types = {'unit': 'VARCHAR'});

INSERT INTO measurement
SELECT unit_id, CAST(test_date AS DATE), model, parameter, value, COALESCE(unit, '')
FROM read_csv('data/clean/measurement_clean.csv', header = true, nullstr = '', types = {'unit': 'VARCHAR', 'value': 'DOUBLE'});

INSERT INTO extraction_eval
SELECT doc, model, revision, format, parameter, field, method, NULLIF(extracted_value, ''), label_value, lower(is_correct) = 'true', NULLIF(error_type, '')
FROM read_csv('results/1-data-preparation/extraction_eval.csv', header = true, all_varchar = true, nullstr = '')
;
