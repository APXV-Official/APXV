# APXV test fixtures

Test vectors for redaction and ZK paths used by the pytest suite.

## Layout

```
tests/fixtures/apxv/
  redaction/     # sample inputs + expected entities (when present)
  zk/            # circuit inputs + expected verify results (when present)
```

Fixtures are added as coverage expands; not all subdirectories exist in every release.