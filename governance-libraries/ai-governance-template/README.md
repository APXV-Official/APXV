# AI Governance Template

**Purpose:**  
A reusable governance library for controlling LLM-powered and tool-using agents within APXV1.

This template provides a baseline set of rules, workflows, and knowledge artifacts designed to ensure that agentic components operate safely, accountably, and in compliance with defined policies.

---

## Contents

- `RULE-AI-001.md` — Core AI governance rules (confidence thresholds, cost limits, human review triggers)
- `WORKFLOW-AI-001.md` — Standard workflow for governed AI decision-making
- `KNOWLEDGE-AI-001.md` — Supporting definitions and terminology

---

## How to Use

**Need a full installable pack?** Use [apxv-pack-ai-governance](../apxv-pack-ai-governance/) (governance specs, `LLMReasoner` pipeline, demo, acceptance tests).

**Custom specs only:**

1. Copy the desired files into your `managed/rules/`, `managed/workflows/`, and `managed/knowledge/` directories.
2. Customize thresholds, rules, and workflows as needed for your specific use case.
3. Reference the rule file hash in your `APX-RULE-xxx` specifications.
4. Apply via propose → approve → apply (see [docs/BUILDING.md](../../docs/BUILDING.md)).

---

## Version

- **Version:** 0.1.0
- **Last Updated:** 2026-06-10

---

*This template is intended to be extended and adapted.*