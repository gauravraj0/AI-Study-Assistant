import os
import tempfile

# Configure isolated storage BEFORE the app imports anything.
_TMP = tempfile.mkdtemp(prefix="aisa-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["VECTOR_STORE_PATH"] = f"{_TMP}/vectors"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-32b"
os.environ["SEED_DEMO"] = "false"
os.environ["LLM_PROVIDER"] = "local"
