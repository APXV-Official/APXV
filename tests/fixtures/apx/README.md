# APX migration test fixtures

Ported test vectors from legacy redaction and ZK suites land here during Phases 1 and 4.

## Layout (planned)

```
tests/fixtures/apx/
  redaction/     # sample inputs + expected entities (Phase 1)
  zk/            # circuit inputs + expected verify (Phase 4)
```

Phase 0 creates this directory only. Fixtures are added phase by phase.