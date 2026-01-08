import base64
import io
import pandas as pd
import requests

# ====== EDIT THESE 3 LINES ONLY ======
GITHUB_OWNER = "avcbeach"     # e.g. "avcbeach"
GITHUB_REPO  = "event-ops-data"   # e.g. "event-ops-data"
GITHUB_BRANCH = "main"
# ====================================

def _headers(token: str):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

def _contents_url(path: str):
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"

def github_read_text(path: str, token: str) -> tuple[str, str]:
    """
    Returns: (text, sha)
    """
    r = requests.get(_contents_url(path), headers=_headers(token), params={"ref": GITHUB_BRANCH})
    r.raise_for_status()
    j = r.json()
    content = base64.b64decode(j["content"]).decode("utf-8")
    return content, j["sha"]

def github_write_text(path: str, text: str, token: str, sha: str, commit_message: str) -> str:
    """
    Writes text to GitHub. Returns new sha.
    """
    payload = {
        "message": commit_message,
        "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }
    r = requests.put(_contents_url(path), headers=_headers(token), json=payload)
    r.raise_for_status()
    return r.json()["content"]["sha"]

def read_csv(path: str, token: str) -> tuple[pd.DataFrame, str]:
    txt, sha = github_read_text(path, token)
    if not txt.strip():
        return pd.DataFrame(), sha
    return pd.read_csv(io.StringIO(txt)), sha

def write_csv(path: str, df: pd.DataFrame, token: str, sha: str, commit_message: str) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return github_write_text(path, buf.getvalue(), token, sha, commit_message)
