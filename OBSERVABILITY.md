# APXV1 — Observability Guide (BYO / DIY)

APXV1 is designed to be **privacy-respecting and minimal by default**. It does **not** include built-in metrics collection or external telemetry.

However, APXV1 provides structured JSON logs that make it easy for users to integrate their own observability stack if desired.

---

## 1. Log Format

All audit and operational logs are written in **structured JSON** by default (one event per line).

Example log entry:

```json
{
  "timestamp": "2026-06-10T12:34:56.789Z",
  "event_type": "llm_reasoner_executed",
  "data": {
    "agent_id": "APX-AGENT-LLM-001",
    "decision": "APPROVED",
    "confidence": 0.85,
    "cost_usd": 0.003,
    "latency_ms": 950
  },
  "current_hash": "...",
  "previous_hash": "..."
}
```

These logs are written to `managed/audit/*.log`.

---

## 2. Integrating with Common Observability Tools

### Loki + Grafana (Recommended for APXV1)

1. Point Loki to the `managed/audit/` directory (or forward the logs via Promtail).
2. Use a simple Promtail scrape config to parse JSON lines.
3. Create dashboards for:
   - Agent execution rates
   - Cost and latency trends
   - Governance rule enforcement events
   - Capability check failures

### Prometheus + Grafana

- Use a log-to-metrics bridge (e.g., `mtail`, `promtail` with relabeling, or a small exporter script).
- Extract counters from log fields like `event_type`, `cost_usd`, `latency_ms`.

### ELK Stack (Elasticsearch + Logstash + Kibana)

- Ingest the JSON logs directly into Elasticsearch.
- Use Kibana to search and visualize events.

### Datadog / New Relic / Other SaaS

- Forward the JSON logs using the vendor’s log shipper.
- Create monitors on key fields (cost, latency, error rates).

---

## 3. Optional Helper Module (DIY)

For users who want a simpler starting point, APXV1 includes an optional helper:

```python
from agents.observability import get_log_metrics, export_to_prometheus
```

See `agents/observability.py` for available helpers.

This module is **completely optional** and not required for normal operation.

---

## 4. Privacy & Data Considerations

- No data is ever sent externally by default.
- All observability is **user-controlled**.
- Users are responsible for configuring their own monitoring stack and ensuring compliance with their data policies.

---

## 5. Recommendation

For most users, the structured JSON logs + an external log aggregation tool (Loki, ELK, etc.) is sufficient and keeps APXV1 lightweight.

Only enable or build additional metrics if you have a specific operational need.

---

*This approach keeps APXV1 minimal while still supporting advanced observability for those who need it.*