"""
APX v1 — Pluggable LLM Backends

Swap in any local or remote LLM by implementing LLMBackend.
APX stays governed: backends return text; agents produce AgenticOutput.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import json
import time
import urllib.error
import urllib.request


@dataclass
class LLMResponse:
    text: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    model: str = ""


class LLMBackend(Protocol):
    """Interface for LLM providers. Implement this to add your own model."""

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        timeout_seconds: int = 30,
    ) -> LLMResponse:
        ...


class SimulatedLLMBackend:
    """Default backend for development and tests — no external calls."""

    def __init__(self, model: str = "simulated"):
        self.model = model

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        timeout_seconds: int = 30,
    ) -> LLMResponse:
        start = time.perf_counter()
        decision = "REVIEW_REQUIRED" if "review" in prompt.lower() else "APPROVED"
        text = (
            f"Simulated reasoning for prompt ({len(prompt)} chars). "
            f"Recommended decision: {decision}."
        )
        if system:
            text += f" System context: {system[:120]}..."
        latency_ms = int((time.perf_counter() - start) * 1000) + 50
        return LLMResponse(
            text=text,
            cost_usd=0.003,
            latency_ms=latency_ms,
            model=self.model,
        )


class OllamaLLMBackend:
    """
    Local Ollama backend (air-gapped friendly when Ollama runs on localhost).

    Requires Ollama running: ollama serve
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2",
        estimated_cost_per_1k_tokens_usd: float = 0.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.estimated_cost_per_1k_tokens_usd = estimated_cost_per_1k_tokens_usd

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        timeout_seconds: int = 30,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama request failed ({self.base_url}). "
                "Is Ollama running locally? See examples/llm-ollama/README.md"
            ) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        text = body.get("response", "").strip()
        eval_count = int(body.get("eval_count", 0) or 0)
        cost = (eval_count / 1000.0) * self.estimated_cost_per_1k_tokens_usd

        return LLMResponse(
            text=text,
            cost_usd=cost,
            latency_ms=latency_ms,
            model=self.model,
        )