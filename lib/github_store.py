import base64
import os
import requests
import streamlit as st

API = "https://api.github.com"

def _get_secret(key: str, default=None):
    # Streamlit Cloud: st.secrets is most reliable
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Fallback: environment variables
    return os.getenv(key, default)

def _cfg():
    token  = _get_secret("GITHUB_TOKEN")  or _get_secret("github_token")
    owner  = _get_secret("GITHUB_OWNER")  or _get_secret("github_owner")
    repo   = _get_secret("GITHUB_REPO")   or _get_secret("github_repo")
    branch = _get_secret("GITHUB_BRANCH") or _get_secret("github_branch") or "main"

    if not owner or not repo:
        raise RuntimeError(
            "Missing GITHUB_OWNER or GITHUB_REPO. "
            "Check Streamlit Secrets keys EXACTLY:\n"
            "GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN, GITHUB_BRANCH"
        )
    return token, owner, repo, branch

def github_read_text(path: str):
    token, owner, repo, branch = _cfg()
    url = f"{API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()

    content = j.get("content", "")
    sha = j.get("sha", "")
    if not content:
        return "", sha

    txt = base64.b64decode(content).decode("utf-8")
    return txt, sha

def github_write_text(path: str, text: str, message: str):
    token, owner, repo, branch = _cfg()
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN (set in Streamlit Secrets).")

    # get sha if file exists
    sha = None
    try:
        _, sha = github_read_text(path)
    except Exception:
        sha = None

    url = f"{API}/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
    }

    payload = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
