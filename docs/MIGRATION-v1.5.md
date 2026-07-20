# Migration: v1.4.x → v1.5.0

## What changes for operators

| Area | v1.4 | v1.5 |
|------|------|------|
| Primary board | Dashboard / Pipeline / Pack Studio | **Workbench** (`/workshop`) |
| Authoring | Pack wizard primary | **Studio** — Agents, Packs, **Proof Profiles** |
| Proofs | Dual-track attest primarily | Proof Profiles + optional **universal-predicate-v1** claim proofs |
| Trust | Separate nav pages | **Trust** hub → Verify / Audit / Governance |
| Jobs label | Jobs | **Runs** (route remains `/jobs`) |

URLs kept for stability: `/workshop`, `/jobs`, `/packs?wizard=1` (advanced wizard).

## Upgrade steps

1. **Backup** — System → Backups, or copy `managed/` (see [RUNBOOK-UPGRADE](../RUNBOOKS/RUNBOOK-UPGRADE.md)).
2. **Install** — desktop installer 1.5.0 or pull the release tag / Docker image for 1.5.0.
3. **Restart** API and UI (desktop: quit fully, then relaunch).
4. **Connect** with your existing operator key (`managed/config/OPERATOR-KEY-*.txt`).
5. **Smoke** — Workbench → load the reference pipeline → Run → open Runs.
6. **Optional sovereign** — if health shows vendor keys, run once:

```bash
python -m scripts.apxv_bootstrap
```

Restart the API afterward.

## Optional: universal predicate keys

For Proof Profiles that attach `universal-predicate-v1` Groth16 proofs:

```bash
python -m scripts.setup_universal_zk
```

See [PROOF-STUDIO.md](PROOF-STUDIO.md).

## Behavior notes

- No forced data migration for packs or audit logs — existing `managed/` state continues.
- UI empty states and CTAs point to **Workbench** and **Studio**.
- Studio **Promote** expects a successful **Test** first.
- Composition runs may bind `proof_profile` in pipeline defaults; claims fail closed if predicates are not met.

## Rollback

Keep the previous desktop installer or git tag `v1.4.0`. Restore `managed/` from backup if needed. No forced schema rewrite in 1.5.0.

## Verify after upgrade

```bash
python -m scripts.apxv_demo --pack reference
# UI: open Workbench, Studio, Runs, and Trust
```
