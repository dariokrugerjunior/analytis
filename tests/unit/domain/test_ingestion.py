"""Tests for ingestion-tracking domain entities."""

from datetime import UTC, datetime

import pytest

from analytis.domain.ingestion import (
    DataSource,
    IngestionRun,
    IngestionStatus,
)


def test_data_source_minimal() -> None:
    ds = DataSource(source_id="footballdata", display_name="Football-Data.org")
    assert ds.source_id == "footballdata"


def test_data_source_id_format() -> None:
    with pytest.raises(ValueError, match="source_id"):
        DataSource(source_id="Football Data", display_name="x")


def test_ingestion_run_default_status() -> None:
    r = IngestionRun(
        data_source_id="footballdata",
        job_name="ingest:fixtures",
        started_at=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert r.status is IngestionStatus.RUNNING


def test_ingestion_run_failed_requires_error() -> None:
    with pytest.raises(ValueError, match="error_message required"):
        IngestionRun(
            data_source_id="footballdata",
            job_name="ingest:fixtures",
            started_at=datetime(2026, 6, 12, tzinfo=UTC),
            status=IngestionStatus.FAILED,
        )
