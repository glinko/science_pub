from enum import StrEnum


class PaperStatus(StrEnum):
    COLLECTED = "collected"
    SCORED = "scored"
    SELECTED = "selected"
    ANALYZED = "analyzed"
    SCRIPTED = "scripted"
    ASSETS_READY = "assets_ready"
    RENDERED = "rendered"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

