"""
Sovereign Phase A gate checks (S2, S6, S7, S8).

Usage:
  py -3 -m scripts.sovereign_gate_checks --all
  py -3 -m scripts.sovereign_gate_checks --s2 --s6 --s7 --s8
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.bootstrap.orchestrator import BootstrapOptions, run_bootstrap as run_bootstrap_orchestrator

API_BASE = "http://127.0.0.1:8741"


def log(msg: str) -> None:
    print(msg, flush=True)


def run_bootstrap(
    base_path: Path,
    *,
    skip_ollama: bool,
    skip_voice: bool,
    skip_smoke: bool,
    profile: str = "production",
) -> dict[str, Any]:
    import os

    prev_base = os.environ.get("APXV_BASE_PATH")
    prev_profile = os.environ.get("APXV_PROFILE")
    os.environ["APXV_BASE_PATH"] = str(base_path.resolve())
    if profile == "ci":
        os.environ["APXV_PROFILE"] = "ci"
    elif profile == "production":
        os.environ.pop("APXV_PROFILE", None)

    try:
        report = run_bootstrap_orchestrator(
            BootstrapOptions(
                base_path=base_path.resolve(),
                source_root=ROOT,
                skip_ollama=skip_ollama,
                skip_voice=skip_voice,
                skip_smoke=skip_smoke,
                skip_prover_build=True,
                profile=profile,
                json_report=False,
            )
        )
        payload = report.to_dict()
        return {
            "exit_code": report.exit_code,
            "report": payload,
            "errors": report.errors,
        }
    finally:
        if prev_base is None:
            os.environ.pop("APXV_BASE_PATH", None)
        else:
            os.environ["APXV_BASE_PATH"] = prev_base
        if prev_profile is None:
            os.environ.pop("APXV_PROFILE", None)
        else:
            os.environ["APXV_PROFILE"] = prev_profile


def read_vk_hashes(base_path: Path) -> dict[str, str]:
    install_path = base_path / "managed" / "config" / "install.json"
    data = json.loads(install_path.read_text(encoding="utf-8"))
    hashes = data.get("vk_hashes") or {}
    return {str(k): str(v) for k, v in hashes.items()}


def check_s2() -> dict[str, Any]:
    """Two fresh bootstraps → different vk_hashes (S2/S4 native)."""
    log("=== S2/S4: two fresh bootstraps → vk_hashes differ ===")
    results: dict[str, Any] = {"id": "S2/S4", "ok": False, "instances": []}

    path_a = Path(tempfile.mkdtemp(prefix="apxv-s2-a-"))
    path_b = Path(tempfile.mkdtemp(prefix="apxv-s2-b-"))

    log(f"  [A] bootstrap → {path_a}")
    run_a = run_bootstrap(
        path_a, skip_ollama=True, skip_voice=True, skip_smoke=True, profile="production"
    )
    log(f"       exit {run_a['exit_code']}")
    if run_a["exit_code"] not in (0, 2) or not run_a["report"]:
        results["error"] = "bootstrap A failed"
        results["run_a"] = run_a
        return results

    log(f"  [B] bootstrap → {path_b}")
    run_b = run_bootstrap(
        path_b, skip_ollama=True, skip_voice=True, skip_smoke=True, profile="production"
    )
    log(f"       exit {run_b['exit_code']}")
    if run_b["exit_code"] not in (0, 2) or not run_b["report"]:
        results["error"] = "bootstrap B failed"
        results["run_b"] = run_b
        return results

    hashes_a = read_vk_hashes(path_a)
    hashes_b = read_vk_hashes(path_b)
    overlap = set(hashes_a.values()) & set(hashes_b.values())
    all_different = len(hashes_a) > 0 and len(overlap) == 0

    results["instances"] = [
        {
            "path": str(path_a),
            "hash_count": len(hashes_a),
            "sample": next(iter(hashes_a.values()), None),
        },
        {
            "path": str(path_b),
            "hash_count": len(hashes_b),
            "sample": next(iter(hashes_b.values()), None),
        },
    ]
    results["overlapping_hashes"] = len(overlap)
    results["ok"] = all_different and run_a["report"].get("sovereign_setup") and run_b["report"].get(
        "sovereign_setup"
    )
    log(f"  RESULT: {'PASS' if results['ok'] else 'FAIL'} — overlapping vk hashes: {len(overlap)}")
    return results


def wait_health(timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_BASE}/api/v2/system/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.5)
    raise TimeoutError(f"API not healthy at {API_BASE}")


def spawn_serve(base_path: Path) -> subprocess.Popen[bytes]:
    py = "py" if _has_py_launcher() else sys.executable
    args = [py, "-3", "-m", "scripts.apxv_serve"] if py == "py" else [py, "-m", "scripts.apxv_serve"]
    return subprocess.Popen(
        args,
        cwd=str(base_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _has_py_launcher() -> bool:
    try:
        subprocess.run(["py", "-3", "--version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_s8() -> dict[str, Any]:
    """Simulated clean desktop path: fresh dir → bootstrap → API healthy (S8)."""
    log("=== S8: simulated clean install → bootstrap → API healthy ===")
    results: dict[str, Any] = {"id": "S8", "ok": False}
    server: subprocess.Popen[bytes] | None = None

    try:
        base = Path(tempfile.mkdtemp(prefix="apxv-s8-clean-"))
        try:
            log(f"  fresh base: {base}")
            run = run_bootstrap(
                base,
                skip_ollama=True,
                skip_voice=True,
                skip_smoke=True,
                profile="production",
            )
            results["bootstrap_exit"] = run["exit_code"]
            if run["exit_code"] not in (0, 2) or not run["report"]:
                results["error"] = "bootstrap failed"
                results["run"] = run
                return results

            sovereign = bool(run["report"].get("sovereign_setup"))
            results["sovereign_setup"] = sovereign

            log("  spawning apxv_serve…")
            server = spawn_serve(base)
            wait_health(60.0)
            with urllib.request.urlopen(f"{API_BASE}/api/v2/system/health", timeout=10) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            results["health"] = health
            results["ok"] = sovereign and health.get("status") in ("healthy", "degraded")
            log(f"  RESULT: {'PASS' if results['ok'] else 'FAIL'} — status={health.get('status')}")
            return results
        finally:
            if server and server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                server = None
    finally:
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


def check_s6_s7() -> dict[str, Any]:
    """Live Ollama + Vosk on production profile (S6/S7)."""
    log("=== S6/S7: production bootstrap with Ollama + Vosk ===")
    results: dict[str, Any] = {"id": "S6/S7", "ok": False}

    base = Path(tempfile.mkdtemp(prefix="apxv-s67-"))
    log(f"  bootstrap with integrations → {base}")
    run = run_bootstrap(
        base,
        skip_ollama=False,
        skip_voice=False,
        skip_smoke=True,
        profile="production",
    )
    results["bootstrap_exit"] = run["exit_code"]
    report = run.get("report") or {}
    install = report.get("install_json") or {}
    ollama = install.get("ollama") or report.get("steps", {}).get("ollama") or {}
    voice = install.get("voice") or report.get("steps", {}).get("voice") or {}
    results["ollama"] = ollama
    results["voice"] = voice

    ollama_ok = bool(ollama.get("verified"))
    voice_ok = bool(voice.get("enabled"))

    # S6: probe AI pack LLM backend when Ollama verified
    llm_real = False
    if ollama_ok:
        try:
            from agents.install_profile import resolve_llm_backend

            backend = resolve_llm_backend(None, base)
            llm_real = type(backend).__name__ not in (
                "SimulatedLLMBackend",
                "SimulatedLLM",
            )
            results["llm_backend"] = type(backend).__name__
        except Exception as exc:
            results["llm_backend_error"] = str(exc)

    results["s6_ollama_verified"] = ollama_ok
    results["s6_llm_not_simulated"] = llm_real
    results["s7_voice_enabled"] = voice_ok
    results["ok"] = ollama_ok and voice_ok and llm_real
    results["partial_ok"] = ollama_ok or voice_ok

    if results["ok"]:
        log("  RESULT: PASS — Ollama verified, Vosk enabled, non-simulated LLM")
    elif results["partial_ok"]:
        log(f"  RESULT: PARTIAL — ollama={ollama_ok} voice={voice_ok} llm_real={llm_real}")
    else:
        log(f"  RESULT: FAIL — ollama={ollama_ok} voice={voice_ok}")
        results["errors"] = run.get("errors")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Sovereign gate checks S2/S6/S7/S8")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--s2", action="store_true")
    parser.add_argument("--s6", action="store_true", help="Includes S7 (same bootstrap run)")
    parser.add_argument("--s7", action="store_true")
    parser.add_argument("--s8", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    if args.all:
        args.s2 = args.s6 = args.s7 = args.s8 = True
    if not any((args.s2, args.s6, args.s7, args.s8)):
        parser.error("Specify --all or one of --s2 --s6 --s7 --s8")

    summary: dict[str, Any] = {"checks": [], "ok": True}

    if args.s2:
        r = check_s2()
        summary["checks"].append(r)
        summary["ok"] &= r["ok"]

    if args.s6 or args.s7:
        r = check_s6_s7()
        summary["checks"].append(r)
        summary["ok"] &= r["ok"]

    if args.s8:
        r = check_s8()
        summary["checks"].append(r)
        summary["ok"] &= r["ok"]

    log("")
    log(f"OVERALL: {'PASS' if summary['ok'] else 'FAIL'}")

    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        log(f"Wrote {args.json_out}")

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())