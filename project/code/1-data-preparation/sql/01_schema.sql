-- Skema database Project 26 (DuckDB). Constraint dicek saat data dimasukkan; baris salah ditolak (lihat constraint_tests.csv).
CREATE TABLE dim_spec (
    model          VARCHAR NOT NULL CHECK (model IN ('5W', '9W', '12W')),
    revision       VARCHAR NOT NULL CHECK (regexp_matches(revision, '^Rev [0-9]\.[0-9]$')),
    valid_from     DATE    NOT NULL,
    parameter      VARCHAR NOT NULL CHECK (parameter IN ('luminous_flux', 'power', 'efficacy', 'cct', 'cri', 'power_factor')),
    lower_limit    DOUBLE,
    upper_limit    DOUBLE,
    unit           VARCHAR NOT NULL,
    source_doc     VARCHAR NOT NULL,
    source_page    INTEGER NOT NULL CHECK (source_page >= 1),
    n_docs_agree   INTEGER NOT NULL,
    n_docs         INTEGER NOT NULL,
    PRIMARY KEY (model, revision, parameter),
    CHECK (lower_limit IS NOT NULL OR upper_limit IS NOT NULL),
    CHECK (lower_limit IS NULL OR upper_limit IS NULL OR lower_limit < upper_limit)
);
CREATE TABLE measurement (
    unit_id    VARCHAR NOT NULL,
    test_date  DATE    NOT NULL,
    model      VARCHAR NOT NULL CHECK (model IN ('5W', '9W', '12W')),
    parameter  VARCHAR NOT NULL CHECK (parameter IN ('luminous_flux', 'power', 'efficacy', 'cct', 'cri', 'power_factor')),
    value      DOUBLE  NOT NULL,
    unit       VARCHAR NOT NULL,
    PRIMARY KEY (unit_id, parameter)
);
CREATE TABLE extraction_eval (
    doc             VARCHAR NOT NULL,
    model           VARCHAR NOT NULL,
    revision        VARCHAR NOT NULL,
    format          VARCHAR NOT NULL,
    parameter       VARCHAR NOT NULL,
    field           VARCHAR NOT NULL CHECK (field IN ('min', 'max', 'unit')),
    method          VARCHAR NOT NULL CHECK (method IN ('rule_basic', 'rule_full', 'llm')),
    extracted_value VARCHAR,
    label_value     VARCHAR NOT NULL,
    is_correct      BOOLEAN NOT NULL,
    error_type      VARCHAR,
    PRIMARY KEY (doc, parameter, field, method)
);
