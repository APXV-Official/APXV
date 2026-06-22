"""
Create (or update) a GitHub Release for an existing tag and upload the verifier bundle.

Requires GITHUB_TOKEN or GH_TOKEN with repo scope.

Example:
  python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle-v1.1.0
  set GITHUB_TOKEN=ghp_...
  python -m scripts.publish_github_release --tag v1.1.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "apxv1dev/APXV1"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def changelog_section(changelog_path: Path, tag: str) -> str:
    """Extract a Keep-a-Changelog section for a tag like v1.1.0."""
    version = tag.lstrip("v")
    text = changelog_path.read_text(encoding="utf-8")
    header = f"## [{version}]"
    start = text.find(header)
    if start < 0:
        raise SystemExit(f"Section not found in {changelog_path}: {header}")
    next_header = text.find("\n## [", start + len(header))
    section = text[start:next_header] if next_header >= 0 else text[start:]
    return section.strip()


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN with repo scope.")
    return token.strip()


def _api(
    method: str,
    url: str,
    token: str,
    *,
    data: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "apxv1-publish-release",
    }
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            body = resp.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API {method} {url} failed ({exc.code}): {detail}") from exc


def _ensure_zip(bundle_dir: Path, zip_path: Path) -> Path:
    if zip_path.exists():
        return zip_path
    if not bundle_dir.exists():
        raise SystemExit(f"Bundle directory not found: {bundle_dir}")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(bundle_dir.rglob("*")):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(bundle_dir.parent))
    return zip_path


def publish_release(
    *,
    tag: str,
    repo: str,
    bundle_zip: Path,
    notes_path: Path,
    draft: bool = False,
) -> str:
    token = _token()
    base = f"https://api.github.com/repos/{repo}"
    if notes_path == CHANGELOG_PATH:
        notes = changelog_section(notes_path, tag)
    else:
        notes = notes_path.read_text(encoding="utf-8")

    release = None
    try:
        release = _api("GET", f"{base}/releases/tags/{tag}", token)
    except SystemExit:
        release = None

    payload = json.dumps(
        {
            "tag_name": tag,
            "name": tag,
            "body": notes,
            "draft": draft,
            "prerelease": False,
        }
    ).encode("utf-8")

    if release:
        release = _api(
            "PATCH",
            f"{base}/releases/{release['id']}",
            token,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
    else:
        release = _api(
            "POST",
            f"{base}/releases",
            token,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

    upload_url = release["upload_url"].split("{")[0]
    asset_name = bundle_zip.name
    with bundle_zip.open("rb") as handle:
        asset_data = handle.read()

    _api(
        "POST",
        f"{upload_url}?name={asset_name}",
        token,
        data=asset_data,
        headers={
            "Content-Type": "application/zip",
            "Content-Length": str(len(asset_data)),
        },
    )

    return release.get("html_url", f"https://github.com/{repo}/releases/tag/{tag}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish GitHub Release with verifier bundle")
    parser.add_argument("--tag", default="v1.1.0")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--bundle-zip",
        type=Path,
        default=ROOT / "dist" / "apxv1-verifier-bundle-v1.1.0.zip",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=ROOT / "dist" / "apxv1-verifier-bundle-v1.1.0",
    )
    parser.add_argument("--notes", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    zip_path = _ensure_zip(args.bundle_dir.resolve(), args.bundle_zip.resolve())
    url = publish_release(
        tag=args.tag,
        repo=args.repo,
        bundle_zip=zip_path,
        notes_path=args.notes.resolve(),
        draft=args.draft,
    )
    print(f"Release published: {url}")
    print(f"  Asset: {zip_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())