import os
import tempfile

import pytest

# config is read at import time, so point it at a temp folder before importing the app
os.environ["DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db  # noqa: E402
from app.main import app, refresh_index  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.init_db()
    refresh_index()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def upload(client, filename, content):
    if isinstance(content, str):
        content = content.encode()
    return client.post("/documents", files=[("files", (filename, content))])
