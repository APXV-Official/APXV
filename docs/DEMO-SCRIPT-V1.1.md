# APXV1 v1.1 — Public Launch Demo Script

**Duration:** ~3 minutes  
**Audience:** Technical buyers, security reviewers, press  
**Prerequisites:** `python -m scripts.setup_first_run`, release Rust binaries built, ceremony transcript written

---

## Act 1 — Trust foundation (30s)

**Terminal 1:**

```powershell
python -m scripts.apx_doctor
python -m scripts.ceremony_transcript --verify
python -m scripts.apx_ctl integrity
```

**Say:** "APXV1 is a local, air-gapped governed agent platform. Doctor confirms ZK keys, policy, and audit chain. The ceremony transcript commits verification key hashes — we publish verifier bundles without proving keys."

**Show:** `HEALTHY`, transcript verify OK, integrity `HEALTHY`.

---

## Act 2 — Text pipeline + dual ZK (60s)

```powershell
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

**Say:** "Three agents: redact under rules, orchestrate workflow, attest with governance and entity Groth16 proofs. Verify re-checks proofs cryptographically — no re-proving."

**Show:** `Entity proofs: VALID`, `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`.

---

## Act 3 — Voice privacy suite (60s)

```powershell
$env:APX_VOICE_MODE='simulated'
python -m scripts.run_apx --voice-transcript "Contact John at john.doe@example.com or call (555) 123-4567." --attest
python -m scripts.verify_attestation --real-zk
```

Or standalone:

```powershell
python -m scripts.run_voice_demo
```

**Say:** "Voice path: speech to text, same redaction engine, voice-redaction ZK circuit proves policy-bound redaction. Self-hosters run their own setup and trust themselves; verifying our demo uses our published verifier bundle."

**Show:** Voice session in artifact, `voice_redaction` proof VALID.

---

## Act 4 — Optional E2EE (20s)

```powershell
python -m scripts.run_apx --attest --encrypt
python -m scripts.verify_attestation --real-zk
```

**Say:** "Artifacts can be encrypted at rest; verify decrypts locally for checks only."

---

## Act 5 — Close (10s)

**Say:** "Governance spine unchanged — rules, audit, capabilities. Privacy layers: redaction, encryption, dual-track ZK, now voice. Independent verify plus signed ceremony transcript. Apache 2.0, runs offline."

**End card:** Repo URL, `v1.1.0` tag, verifier bundle on Releases.

---

## Recording tips

- Font size 16+, dark theme, 1920×1080
- Pre-run once to warm Rust caches; record second run
- Compress with same settings as `apxv1-demo.mp4` (see README)