"""Download Actions artifacts using the user's existing Git credential manager.

Never prints or stores the credential; strips it before following storage redirects.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile
from common import ROOT, BUILD


class StorageRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urllib.parse.urlsplit(newurl).hostname != "api.github.com":
            redirected.remove_header("Authorization")
        return redirected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_id", type=int)
    parser.add_argument("--repo", default="wizzwu/todo")
    args = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo)
    result = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True,
                            text=True, check=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"))
    credential = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    headers = {"Authorization": "Bearer " + credential["password"], "Accept": "application/vnd.github+json"}
    opener = urllib.request.build_opener(StorageRedirect())
    endpoint = f"https://api.github.com/repos/{args.repo}/actions/artifacts/{args.artifact_id}"
    with opener.open(urllib.request.Request(endpoint, headers=headers), timeout=60) as response:
        metadata = json.load(response)
    assert re.fullmatch(r"[A-Za-z0-9_.-]+", metadata["name"]) and metadata["name"] not in (".", ".."), "Unsafe artifact name"
    folder = BUILD / "cloud" / str(metadata["workflow_run"]["id"]) / metadata["name"]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "artifact.zip"
    with opener.open(urllib.request.Request(endpoint + "/zip", headers=headers), timeout=120) as response, target.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert metadata.get("digest") in (None, "sha256:" + digest), "Artifact digest mismatch"
    with zipfile.ZipFile(target) as archive:
        for entry in archive.infolist():
            resolved = (folder / entry.filename).resolve()
            assert resolved.is_relative_to(folder.resolve()), "Unsafe artifact path"
        archive.extractall(folder)
    (folder / "artifact-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Downloaded and verified {metadata['name']} into {folder}")


if __name__ == "__main__":
    main()
