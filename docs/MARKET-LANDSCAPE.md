# APX — Market Landscape & Competitive Position

**Last updated:** 2026-06-17  
**Purpose:** Honest scan before OSS release — who overlaps, who beats APX on what, and how to position without overclaiming.

Related: [PROJECT-OVERVIEW.md](../PROJECT-OVERVIEW.md), [SECURITY.md](../SECURITY.md), [README.md](../README.md).

---

## How to read this document

APX is best understood as **integration of several mature problem areas**, not as a single feature racing one competitor.

| Mental model | Accurate? |
|--------------|-----------|
| “Someone already shipped APX but better” | **No** — no public OSS found that combines the full APX stack |
| “Specialists beat APX on individual layers” | **Yes** — governance wrappers, enterprise crypto-governance, zkML, framework ecosystems |
| “APX is one of a kind as a whole” | **Yes** — local platform + markdown governance lifecycle + signed capabilities + artifact/audit chain + Groth16 rule-binding proofs |
| “APX beats specialists at their own layer” | **No** — don’t claim that in README or talks |

**One-line positioning:** APX is the **only integrated air-gapped governed-agent platform with ZK rule-binding proofs** found in this scan — but it is **not** the best policy wrapper, best enterprise attestation product, or best LLM framework.

---

## What APX is (for comparison)

**APX — Attested Proof eXecution** (working expansion): a local, air-gapped platform where agents run under signed capabilities, governance specs live in markdown with an approval workflow, outputs are immutable artifacts, audit is chained, and Groth16 proofs bind execution to rule/workflow hashes.

Four layers APX combines:

1. **Agent governance** — policy, capabilities, audit
2. **Cryptographic attestation** — prove what ran and under which rules
3. **Air-gapped / self-hosted runtime** — no cloud dependency
4. **ZK proofs** — Groth16 over governance binding (not full LLM inference)

Most market players cover **one or two** of these. APX ships **all four in one repo**.

---

## Closest market players (2025–2026)

### 1. Microsoft Agent Governance Toolkit (AGT)

| | |
|--|--|
| **What** | OSS toolkit — YAML policy, tamper-evident audit, identity, sandboxing, formal specs, LangChain/CrewAI/MCP integrations |
| **Links** | [microsoft.github.io/agent-governance-toolkit](https://microsoft.github.io/agent-governance-toolkit/) · [GitHub](https://github.com/microsoft/agent-governance-toolkit) |
| **Scale** | 3,700+ GitHub stars, multi-language SDKs, 10 formal specs |
| **Beats APX on** | Framework integrations, ecosystem reach, compliance mapping (OWASP, NIST, EU AI Act), production governance narrative |
| **APX beats AGT on** | Integrated local runtime, markdown governance lifecycle, immutable artifact store, Groth16 rule-binding proofs, air-gapped-first design |
| **Not the same product** | AGT **wraps** existing agents; APX **is** a platform you build on |

---

### 2. Attested Intelligence — Cryptographic Runtime Governance (CRG)

| | |
|--|--|
| **What** | Commercial “cryptographic runtime governance” — sealed Ed25519 artifacts, continuous measurement, signed receipts, Merkle evidence bundles, offline verification |
| **Links** | [attestedintelligence.com/cryptographic-runtime-governance](https://attestedintelligence.com/cryptographic-runtime-governance) |
| **Beats APX on** | Enterprise narrative, continuous enforcement model, evidence-bundle spec, category definition |
| **APX beats CRG on** | OSS/self-host, Groth16 proofs (CRG explicitly distinguishes itself from ZK attestation), markdown governance workflow, reference pipeline you can run locally today |
| **Not the same product** | CRG = continuous portal enforcement + Merkle receipts; APX = governed pipeline + ZK binding to rule hashes |

---

### 3. aflock

| | |
|--|--|
| **What** | Signed `.aflock` policies constraining agent behavior — MCP, JWT + server-side signing, sub-agent delegation (Go) |
| **Links** | [github.com/aflock-ai/aflock](https://github.com/aflock-ai/aflock) · [aflock.ai](https://aflock.ai) |
| **Scale** | Early / spec phase (~24 stars at time of scan) |
| **Beats APX on** | MCP-native agent identity, spend limits, tool/file grants for coding agents |
| **APX beats aflock on** | Full runtime (store, audit, governance approval, API, Docker, ZK, reference pipeline) |
| **Not the same product** | aflock = policy lockfile for agents; APX = governed processing platform |

---

### 4. Agent Control Standard (ACS)

| | |
|--|--|
| **What** | Open standard/framework for runtime governance (spec + community) |
| **Links** | [agentcontrolstandard.org](https://agentcontrolstandard.org/) · [GitHub](https://github.com/Agent-Control-Standard/ACS) |
| **Beats APX on** | Standards-body credibility, cross-vendor framing |
| **APX beats ACS on** | Runnable platform, not just a spec |
| **Relationship** | Complementary — APX could align with ACS-style controls over time |

---

### 5. LangGraph / LangSmith

| | |
|--|--|
| **What** | Agent graphs, governance checkpoint patterns, enterprise observability, self-hosted options |
| **Links** | [docs.langchain.com](https://docs.langchain.com/) |
| **Beats APX on** | LangChain ecosystem, graph orchestration, hosted/enterprise ops |
| **APX beats LangGraph on** | Air-gapped-first, ZK, markdown-native governance lifecycle, no framework lock-in |
| **Not the same buyer** | Teams already on LangChain vs teams building self-hosted governed runtimes |

---

### 6. Enterprise confidential / air-gapped AI

| | |
|--|--|
| **Examples** | Opaque, Fortanix, TrueFoundry air-gapped LLM deploy |
| **Beats APX on** | Confidential computing (TEE), enterprise sales, scale deployment for regulated LLMs |
| **APX beats them on** | Governed agent **platform** with rule proofs — not GPU/confidential VM infrastructure |
| **Layer** | Infrastructure vs application platform |

---

### 7. ZK + AI (zkML, research)

| | |
|--|--|
| **Examples** | [EZKL](https://github.com/zkonduit/ezkl), Lagrange DeepProve, ZK-MCP audit papers (arXiv) |
| **Beats APX on** | Proving **model inference** (ONNX/PyTorch circuits), research depth on zkML |
| **APX beats them on** | Proving **governance binding** (rule/workflow/redaction) on a deterministic pipeline — different claim, less crowded |
| **Industry gap** | Research still notes few **full end-to-end verifiable pipeline** implementations (preprocess + inference + tools + governance) |

---

## Feature matrix (honest)

| Capability | APX v0.3.0 | MS AGT | Attested CRG | aflock | LangGraph+Smith |
|------------|------------|--------|--------------|--------|-----------------|
| OSS & self-host | Yes | Yes | Partial / commercial | Yes (early) | Partial |
| Air-gapped-first | Yes | Partial | Yes (verify offline) | Partial | Weak |
| Signed agent policy | Yes | Yes | Yes (sealed artifact) | Yes | Partial |
| Tamper-evident audit | Yes | Yes | Yes (receipt chain) | Yes | Yes |
| Markdown governance specs | Yes | YAML policies | Sealed artifact | JSON policy | Various |
| Governance change workflow | Yes | Partial | Seal-time | Policy file | Varies |
| Immutable artifact store | Yes | Not core | Evidence bundles | No | Traces |
| Groth16 ZK proofs | Yes | No | No (by design) | No | No |
| Framework integrations | Minimal | Extensive | N/A | MCP | Native |
| Prove LLM inference | No | No | No | No | No |
| Maturity / backing | Solo, pre-release | Microsoft | Commercial | Early | LangChain ecosystem |

---

## Where APX wins (lead with these)

1. **Integrated local platform** — store, audit, API, Docker, setup/doctor — not a bolt-on library.
2. **Governance-as-markdown** — rules, workflows, knowledge with propose → approve → apply.
3. **ZK over governance binding** — proofs tie execution to rule/workflow hashes; most tools stop at logs and signatures.
4. **Air-gapped / no telemetry** — credible for privacy-sensitive and offline prototyping.

---

## Where APX loses (say this publicly)

| Gap | Who is stronger |
|-----|-----------------|
| Framework integrations (LangChain, CrewAI, MCP) | Microsoft AGT |
| Stars, docs polish, enterprise GTM | Microsoft, Attested Intelligence |
| Tool-call / coding-agent policy at scale | AGT, aflock |
| Prove frontier LLM inference | EZKL, Lagrange (still limited) |
| Compliance certifications | Enterprise vendors |
| DLP-grade PII redaction | Commercial privacy/redaction tools |

---

## Claims that would make you look bad

- “First governed AI platform ever”
- “Production compliance certified (HIPAA/SOC2)”
- “Better than Microsoft AGT at framework integration”
- “ZK proves your LLM reasoning is correct”
- “Full verifiable end-to-end LLM pipeline”

## Claims that are credible

- “Open-source **air-gapped platform foundation** for governed agent systems”
- “Markdown rules + signed capabilities + audit chains + **Groth16 proofs that execution matched policy hashes**”
- “Research foundation — bring your own agents and LLMs”
- “Deterministic reference pipeline; not a LangChain wrapper”

---

## FAQ — “Am I copying anyone?”

**Q: Is APX copying an existing product?**  
**A:** No. The **combination** (local platform + markdown governance lifecycle + capabilities + artifact/audit chain + Groth16 rule-binding) was not found as a single public OSS product in this scan.

**Q: Are specialists better than APX at parts of what APX does?**  
**A:** Yes. Microsoft AGT is stronger on **governance for popular frameworks**. Attested Intelligence is stronger on **enterprise cryptographic governance narrative**. LangChain is stronger on **agent orchestration ecosystem**. zkML projects are stronger on **proving model inference**.

**Q: So APX is unique but made of parts others do better?**  
**A:** That is the right gist. APX is **integration architecture** — like building a car from components where Bosch makes better brakes and Michelin makes better tires, but **your chassis + assembly** is what does not exist elsewhere in this form.

**Q: Is “Attested Proof eXecution” a crowded name/category?**  
**A:** The **words** overlap (attestation, proof, execution are everywhere in 2026). The **product shape** does not. Position on **what the integrated system does**, not on owning the acronym.

---

## Portfolio vs business (from landscape)

| Path | Verdict |
|------|---------|
| **Portfolio / OSS credibility** | Strong — real 2026 topic, differentiated integration, demonstrable end-to-end |
| **Compete with Microsoft on breadth** | Weak — wrong fight |
| **Niche business** | Possible — air-gapped, proof-oriented, self-hosted governed agents for privacy-sensitive teams; requires vertical product layer on top |

---

## References (external)

- [Microsoft Agent Governance Toolkit](https://microsoft.github.io/agent-governance-toolkit/)
- [Attested Intelligence — CRG](https://attestedintelligence.com/cryptographic-runtime-governance)
- [aflock](https://github.com/aflock-ai/aflock)
- [Agent Control Standard](https://agentcontrolstandard.org/)
- [Zylos — ZK for AI agent verification](https://zylos.ai/research/2026-03-18-zero-knowledge-proofs-ai-agent-verification)
- [awesome-ai-agent-governance](https://github.com/systempromptio/awesome-ai-agent-governance) — curated list to re-check periodically

---

## Re-scan before major release

Before v0.4.0 or any “we’re production-ready” push, re-run a 30-minute scan:

1. GitHub: `agent governance toolkit`, `signed agent policy`, `zk agent attestation`
2. Check Microsoft AGT changelog and star count
3. Check Attested Intelligence / aflock releases
4. Update this file’s “Last updated” and matrix if needed