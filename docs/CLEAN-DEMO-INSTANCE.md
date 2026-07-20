# Clean demo instance

Resets Studio catalog and removes ephemeral Studio agents/proofs so a machine
matches a clean operator demo. Does **not** delete official packs under
`governance-libraries/apxv-pack-*`.

```powershell
# From repository root
Remove-Item -Recurse -Force managed\studio\agents\* -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force managed\studio\packs\* -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force managed\studio\proofs\* -ErrorAction SilentlyContinue
python -c "from pathlib import Path; import json; Path('managed/studio/catalog.json').write_text(json.dumps({'agents':{},'packs':{},'proofs':{},'updated_at':None},indent=2)+chr(10))"
```

Keep official packs (reference redaction, document processing, AI governance) and
any pipelines you still want under `managed/pipelines/` or `examples/pipelines/`.
