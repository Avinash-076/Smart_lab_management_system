import sys
from pathlib import Path

# Ensure both workspace root and client_agent directory are on sys.path
TEST_DIR = Path(__file__).resolve().parent
CLIENT_AGENT_ROOT = TEST_DIR.parent
WORKSPACE_ROOT = CLIENT_AGENT_ROOT.parent

for p in (str(WORKSPACE_ROOT), str(CLIENT_AGENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
