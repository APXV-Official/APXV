# APXV1 Migration Baseline

Recorded at Phase 0. Re-run before each phase merge to confirm no regressions.

## Environment

| Item | Value |
|------|-------|
| Workspace | `C:\APXV1` |
| Branch | `apx-v1-migration` |
| Python | `python -m pytest` |

## Commands

```powershell
cd C:\APXV1
python -m pytest --tb=short -q
```

```powershell
cargo test --manifest-path rust/Cargo.toml
```

## Results

| Suite | Expected | Actual | Date |
|-------|----------|--------|------|
| pytest | 51 passed | **307 passed** (v1.1: voice + ceremony + dual ZK E2E) | 2026-06-22 |
| rust workspace | builds clean | apx-zk + apx-circuits tests pass in CI | 2026-06-22 |

## Notes

- Legacy reference folders gitignored; not part of baseline.
- `rust/apx-circuits/keys/manifest.json` may show local modifications — expected.