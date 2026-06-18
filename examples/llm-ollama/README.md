# Ollama LLM Example

Plug a **local** LLM into APX without changing the governance layer.

## Prerequisites

1. APX setup complete: `python -m scripts.setup_first_run`
2. [Ollama](https://ollama.com) installed and running locally:

```bash
ollama serve
ollama pull llama3.2
```

Ollama stays on `127.0.0.1` — consistent with APX's local-first design.

## Run

```bash
python examples/llm-ollama/run_llm_agent.py "Should this document be approved for release?"
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