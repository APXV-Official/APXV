"""
APXV — Ollama LLM Agent Example

Shows how to plug a local LLM into APXV using the LLMBackend interface.
Requires Ollama running on localhost (ollama serve).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.llm_backend import OllamaLLMBackend
from agents.llm_reasoner import LLMReasoner
from agents.runtime import APXRuntime


def main() -> int:
    prompt = " ".join(sys.argv[1:]) or "Summarize why governed local agents matter for privacy."

    runtime = APXRuntime()
    backend = OllamaLLMBackend(model="llama3.2")
    agent = LLMReasoner(runtime=runtime, backend=backend)

    try:
        output = agent.execute({"prompt": prompt})
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print("Tip: start Ollama locally, pull a model: ollama pull llama3.2", file=sys.stderr)
        return 1

    print(json.dumps(output.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())