"""
Pytest configuration and test isolation fixtures.
"""
import pytest
import os
import glob

@pytest.fixture(autouse=True, scope="session")
def cleanup_sqlite_dbs():
    for f in glob.glob("*.db") + glob.glob("services/*/*.db"):
        try:
            os.remove(f)
        except Exception:
            pass
    yield
    for f in glob.glob("*.db") + glob.glob("services/*/*.db"):
        try:
            os.remove(f)
        except Exception:
            pass
