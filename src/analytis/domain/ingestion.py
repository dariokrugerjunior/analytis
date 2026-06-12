"""Domain entities for ingestion observability."""

import re
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import IngestionRunId

_SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9_\-]+$")


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DataSource(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=2, max_length=50)
    display_name: str = Field(min_length=1, max_length=200)
    homepage_url: str | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_id(self) -> "DataSource":
        if not _SOURCE_ID_PATTERN.match(self.source_id):
            raise ValueError("source_id must match [a-z0-9_-] (lowercase, no spaces)")
        return self


class IngestionRun(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: IngestionRunId = Field(default_factory=uuid4)
    data_source_id: str
    job_name: str = Field(min_length=1, max_length=100)
    started_at: datetime
    finished_at: datetime | None = None
    status: IngestionStatus = IngestionStatus.RUNNING
    records_touched: int = Field(default=0, ge=0)
    error_message: str | None = None
    payload_hash: str | None = None

    @model_validator(mode="after")
    def _validate_status(self) -> "IngestionRun":
        if self.status is IngestionStatus.FAILED and not self.error_message:
            raise ValueError("error_message required when status=failed")
        if self.status is IngestionStatus.SUCCEEDED and not self.finished_at:
            raise ValueError("finished_at required when status=succeeded")
        return self
