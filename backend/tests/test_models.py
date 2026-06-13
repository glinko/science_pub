from app.enums import JobStatus, PaperStatus
from app.models.job import JobRecord
from app.models.paper import Paper


def test_sqlalchemy_enums_bind_lowercase_values() -> None:
    assert Paper.__table__.c.status.type.enums == [status.value for status in PaperStatus]
    assert JobRecord.__table__.c.status.type.enums == [status.value for status in JobStatus]
