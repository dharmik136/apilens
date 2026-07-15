-- api_logs table for correlated log ingestion (auto error-trace capture)
-- Migration: 004_api_logs
--
-- Column set mirrors apps/ingest/app/ingest.py:LOG_COLUMNS exactly so the
-- INSERT INTO api_logs (...) statement in handle_logs() has a matching
-- schema, and so ensure_clickhouse_schema()'s defensive
-- `ALTER TABLE api_logs ADD COLUMN IF NOT EXISTS ...` statements are no-ops
-- against a freshly migrated database.

CREATE TABLE IF NOT EXISTS api_logs (
    timestamp DateTime64(3) CODEC(DoubleDelta, ZSTD(1)),
    app_id String CODEC(ZSTD(1)),
    project_id String CODEC(ZSTD(1)),
    environment LowCardinality(String) CODEC(ZSTD(1)),
    level LowCardinality(String) CODEC(ZSTD(1)),
    message String CODEC(ZSTD(1)),
    logger_name String CODEC(ZSTD(1)),
    endpoint_method LowCardinality(String) CODEC(ZSTD(1)),
    endpoint_path String CODEC(ZSTD(1)),
    status_code UInt16 CODEC(ZSTD(1)),
    consumer_id String CODEC(ZSTD(1)),
    consumer_name String CODEC(ZSTD(1)),
    consumer_group String CODEC(ZSTD(1)),
    trace_id String CODEC(ZSTD(1)),
    span_id String CODEC(ZSTD(1)),
    payload String CODEC(ZSTD(3)),
    attributes_json String CODEC(ZSTD(3))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (app_id, environment, level, timestamp)
TTL toDateTime(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

ALTER TABLE api_logs ADD INDEX IF NOT EXISTS idx_api_logs_app_id app_id TYPE bloom_filter(0.01) GRANULARITY 1;
ALTER TABLE api_logs ADD INDEX IF NOT EXISTS idx_api_logs_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1;
ALTER TABLE api_logs ADD INDEX IF NOT EXISTS idx_api_logs_trace_id trace_id TYPE bloom_filter(0.01) GRANULARITY 1;
