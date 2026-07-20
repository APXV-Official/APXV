import { formatDisplayValue } from "./format-value";

export function formatDoctorCheckSummary(
  name: string,
  detail: unknown,
  ok: boolean,
): string {
  if (name === "integrity" && detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    const audit = d.audit_logs as Record<string, boolean> | undefined;
    const broken = audit
      ? Object.entries(audit)
          .filter(([, valid]) => !valid)
          .map(([log]) => log)
      : [];
    if (broken.length > 0) {
      return `Audit chain broken: ${broken.join(", ")}. Use Repair audit chain.`;
    }
    if (!ok) {
      return "Integrity check failed — see System page for details.";
    }
    return "Store, audit, policy, and governance all valid.";
  }

  if (name === "sovereign_setup" && detail && typeof detail === "object") {
    const d = detail as {
      status?: string;
      issues?: string[];
      vendor_circuits?: string[];
    };
    if (d.vendor_circuits && d.vendor_circuits.length > 0) {
      return `Vendor keys detected (${d.vendor_circuits.join(", ")}). Run sovereign bootstrap.`;
    }
    if (d.issues && d.issues.length > 0) {
      return d.issues.join("; ");
    }
    if (ok) {
      return "Operator-generated keys with matching install.json provenance.";
    }
    return "Sovereign setup incomplete — run apxv_bootstrap.";
  }

  if (name.startsWith("zk_keys") && detail && typeof detail === "object") {
    const circuits = detail as Record<string, { ready?: boolean }>;
    const total = Object.keys(circuits).length;
    const ready = Object.values(circuits).filter((c) => c.ready).length;
    return `${ready}/${total} circuits ready`;
  }

  if (name === "capability_policy" && detail && typeof detail === "object") {
    const d = detail as { policy_verified?: boolean; total_agents?: number };
    return d.policy_verified
      ? `Policy verified (${d.total_agents ?? "?"} agents)`
      : "Policy not verified";
  }

  if (typeof detail === "string" || typeof detail === "number") {
    return String(detail);
  }

  if (detail && typeof detail === "object") {
    const text = formatDisplayValue(detail);
    return text.length > 120 ? `${text.slice(0, 120)}…` : text;
  }

  return formatDisplayValue(detail);
}

/** True only when an audit log chain is broken (repairable). Not vendor-key degradation. */
export function auditChainBroken(
  checks: Array<{ name?: string; ok?: boolean; detail?: unknown }> | null | undefined,
): boolean {
  const integrity = checks?.find((c) => c.name === "integrity");
  if (!integrity || integrity.ok) return false;
  const detail = integrity.detail;
  if (!detail || typeof detail !== "object") return false;
  const d = detail as Record<string, unknown>;
  if (d.all_audit_valid === false) return true;
  const audit = d.audit_logs as Record<string, boolean> | undefined;
  if (audit && Object.values(audit).some((v) => v === false)) return true;
  return false;
}

/** @deprecated use auditChainBroken — integrity can fail for sovereign/vendor keys too */
export function integrityCheckFailed(
  checks: Array<{ name?: string; ok?: boolean; detail?: unknown }> | null | undefined,
): boolean {
  return auditChainBroken(checks);
}

/** Vendor/default proving keys (safe to operate; bootstrap for operator-sovereign keys). */
export function sovereignVendorKeysOnly(
  checks: Array<{ name?: string; ok?: boolean; detail?: unknown }> | null | undefined,
): boolean {
  const s = checks?.find((c) => c.name === "sovereign_setup");
  if (!s || s.ok) return false;
  const detail = s.detail;
  if (!detail || typeof detail !== "object") return true;
  const d = detail as { status?: string; vendor_circuits?: string[] };
  return (
    d.status === "vendor_keys" ||
    (Array.isArray(d.vendor_circuits) && d.vendor_circuits.length > 0)
  );
}