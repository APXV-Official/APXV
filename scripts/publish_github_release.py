"""
Create (or update) a GitHub Release for an existing tag and upload the verifier bundle.

Requires GITHUB_TOKEN or GH_TOKEN with repo scope.

Example:
  python -m scripts.export_verifier_bundle --out dist/apxv-verifier-bundle-v1.1.0
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
DEFAULT_REPO = "APXV-Official/APXV"
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


def _upload_asset(upload_url: str, token: str, asset_path: Path) -> None:
    suffix = asset_path.suffix.lower()
    content_types = {
        ".zip": "application/zip",
        ".msi": "application/x-msi",
        ".exe": "application/octet-stream",
        ".deb": "application/vnd.debian.binary-package",
        ".appimage": "application/octet-stream",
    }
    content_type = content_types.get(suffix, "application/octet-stream")
    asset_data = asset_path.read_bytes()
    _api(
        "POST",
        f"{upload_url}?name={asset_path.name}",
        token,
        data=asset_data,
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(asset_data)),
        },
    )


def publish_release(
    *,
    tag: str,
    repo: str,
    bundle_zip: Optional[Path],
    extra_assets: list[Path],
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
    uploaded: list[str] = []
    if bundle_zip is not None:
        _upload_asset(upload_url, token, bundle_zip)
        uploaded.append(bundle_zip.name)
    for asset in extra_assets:
        _upload_asset(upload_url, token, asset)
        uploaded.append(asset.name)

    url = release.get("html_url", f"https://github.com/{repo}/releases/tag/{tag}")
    if uploaded:
        print("  Assets:")
        for name in uploaded:
            print(f"    - {name}")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or update a GitHub Release and upload assets"
    )
    parser.add_argument("--tag", default="v1.3.1")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--bundle-zip",
        type=Path,
        default=None,
        help="Verifier bundle zip (optional)",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Verifier bundle directory (zipped when --bundle-zip set)",
    )
    parser.add_argument(
        "--asset",
        type=Path,
        action="append",
        default=[],
        help="Additional release asset (repeatable; e.g. MSI, deb, AppImage)",
    )
    parser.add_argument("--notes", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    zip_path: Optional[Path] = None
    if args.bundle_zip is not None:
        bundle_dir = args.bundle_dir or args.bundle_zip.with_suffix("")
        zip_path = _ensure_zip(bundle_dir.resolve(), args.bundle_zip.resolve())

    extra_assets = [path.resolve() for path in args.asset]
    for path in extra_assets:
        if not path.is_file():
            raise SystemExit(f"Asset not found: {path}")
    if zip_path is None and not extra_assets:
        raise SystemExit("Provide --bundle-zip and/or one or more --asset paths.")

    url = publish_release(
        tag=args.tag,
        repo=args.repo,
        bundle_zip=zip_path,
        extra_assets=extra_assets,
        notes_path=args.notes.resolve(),
        draft=args.draft,
    )
    print(f"Release published: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())