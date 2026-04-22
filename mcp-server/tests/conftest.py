import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from db import init_db, get_connection

@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    import db as db_mod
    monkeypatch.setattr(db_mod, "KB_PATH", db_path)  # all tool modules resolve KB_PATH from db at call time
    return db_path
