import base64
import os
import requests

def _cfg():
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")

    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN (set it in Streamlit Secrets).")
    if not owner or not repo:
        raise RuntimeError("Missing GITHUB_OWNER or GITHUB_REPO (set in Streamlit Secrets).")
    return token, owner, repo, branch

def github_read_text(path: str) -> tuple[str, str | None]:
    token, owner, repo, branch = _cfg()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        return "", None
    r.raise_for_status()
    j = r.json()
    content = base64.b64decode(j["content"]).decode("utf-8")
    return content, j["sha"]

def github_write_text(path: str, text: str, message: str):
    token, owner, repo, branch = _cfg()

    # get sha if file exists
    _, sha = github_read_text(path)

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    payload = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()
