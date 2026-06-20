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
| pytest | 51 passed | **123 passed** (Phase 1 gate) | 2026-06-20 |
| rust (apx-circuits) | builds clean | **0 tests** (no unit tests in crate yet); `cargo test` ok | 2026-06-20 |

## Notes

- Legacy reference folders gitignored; not part of baseline.
- `rust/keys/manifest.json` may show local modifications — expected.