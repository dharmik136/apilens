-- api_spans table for distributed trace spans (the trace waterfall view)
-- Migration: 005_api_spans
--
-- Previously only created at runtime (CREATE TABLE IF NOT EXISTS), in two
-- separate places — apps/api/apps/projects/services.py's
-- ensure_api_spans_table and apps/ingest/app/ingest.py's
-- ensure_clickhouse_schema — with no migration file and no shared source of
-- truth, which had already let their index sets drift apart. This is now
-- the canonical definition. Both runtime copies remain as no-op safety nets
-- (CREATE/ADD INDEX IF NOT EXISTS) for pre-existing databases that predate
-- this migration.
--
-- The legacy `traces` table from 001_initial_schema (tenant_id model) is
-- intentionally unused and unrelated to this one.

CREATE TABLE IF NOT EXISTS api_spans (
    timestamp DateTime64(3) CODEC(DoubleDelta, ZSTD(1)),
    app_id String CODEC(ZSTD(1)),
    project_id String CODEC(ZSTD(1)),
    environment LowCardinality(String) CODEC(ZSTD(1)),
    trace_id String CODEC(ZSTD(1)),
    span_id String CODEC(ZSTD(1)),
    parent_span_id String CODEC(ZSTD(1)),
    name String CODEC(ZSTD(1)),
    kind LowCardinality(String) CODEC(ZSTD(1)),
    service_name LowCardinality(String) CODEC(ZSTD(1)),
    duration_ms Float64 CODEC(Gorilla, ZSTD(1)),
    status LowCardinality(String) CODEC(ZSTD(1)),
    status_code UInt16 CODEC(ZSTD(1)),
    attributes_json String CODEC(ZSTD(3))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (app_id, trace_id, timestamp)
TTL toDateTime(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

ALTER TABLE api_spans ADD INDEX IF NOT EXISTS idx_api_spans_trace_id trace_id TYPE bloom_filter(0.01) GRANULARITY 1;
ALTER TABLE api_spans ADD INDEX IF NOT EXISTS idx_api_spans_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1;
ALTER TABLE api_spans ADD INDEX IF NOT EXISTS idx_api_spans_environment environment TYPE bloom_filter(0.01) GRANULARITY 1;
