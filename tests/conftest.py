import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client(tmp_path, monkeypatch):
    import cache

    monkeypatch.setattr(cache, "DATABASE_PATH", str(tmp_path / "cache.db"))
    cache.inicializar_cache()

    from app import app

    return app.test_client()
