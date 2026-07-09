# Ollama LLM Example

plug a **local** LLM into APXV without changing the governance layer.

## Prerequisites

1. APXV setup complete: `python -m scripts.setup_first_run`
2. [Ollama](https://ollama.com) installed and running locally:

```bash
ollama serve
ollama pull llama3.2
```

Ollama stays on `127.0.0.1` — consistent with APXV's local-first design.

## Run

```bash
python examples/llm-ollama/run_llm_agent.py "Should this document be approved for release?"
```

On Linux/WSL use `python3` if `python` is not on PATH.

## Timeout

`LLMReasoner` enforces a wall-clock limit per call. Default is **120 seconds** (v1.2.1+). Slow CPU inference may need more:

```bash
export APX_LLM_TIMEOUT_SECONDS=180
python examples/llm-ollama/run_llm_agent.py "Your prompt"
```

## How It Works

1. `OllamaLLMBackend` implements `LLMBackend`
2. `LLMReasoner` enforces capabilities, cost/latency limits, governance rules
3. Output is structured `AgenticOutput` written as a governed artifact

## Use Your Own LLM

Implement `LLMBackend` in `agents/llm_backend.py` pattern:

```python
class MyLLMBackend:
    def complete(self, prompt, *, system="", timeout_seconds=30) -> LLMResponse:
        ...
```

Pass it to `LLMReasoner(runtime=runtime, backend=MyLLMBackend())`.

See [docs/BUILDING.md](../../docs/BUILDING.md) for the full extension guide.