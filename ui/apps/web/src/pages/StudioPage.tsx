/**
 * APXV Studio — create Agents, Packs, and Proof Profiles; test; promote to Workbench.
 */
import {
  compileProofIntent,
  getProofStudioStatus,
  listProofCatalog,
  listProofTemplates,
  listStudioAgents,
  listStudioPacks,
  listStudioProofs,
  promoteStudioAgent,
  promoteStudioPack,
  promoteStudioProof,
  saveStudioAgent,
  saveStudioPack,
  saveStudioProof,
  saveStudioProofFromIntent,
  saveStudioProofFromTemplate,
  testStudioAgent,
  testStudioPack,
  testStudioProof,
  type ProofPredicate,
  type StudioAgent,
  type StudioPack,
  type StudioProof,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Badge,
  Button,
  DataSurface,
  Input,
  Label,
  SectionHeader,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";

type Tab = "agents" | "packs" | "proofs";

const DEFAULT_PROOF_PREDICATES = [
  "REDACTION_NONEMPTY",
  "RULE_BOUND",
  "PIPELINE_CHAIN",
  "ATTESTED_STATUS",
  "GOVERNANCE_APPROVED",
];

function studioTestPassed(
  last?: { final_status?: string; ok?: boolean } | null,
): boolean {
  if (!last) return false;
  if (last.ok === true) return true;
  const s = (last.final_status || "").toLowerCase();
  return s === "succeeded" || s === "completed" || s === "ok" || s === "passed";
}

export function StudioPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { tab: tabParam } = useSearch({ from: "/shell/studio" });
  const [tab, setTab] = useState<Tab>(
    tabParam === "packs" || tabParam === "proofs" || tabParam === "agents"
      ? tabParam
      : "agents",
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forcePromote, setForcePromote] = useState<{
    kind: "agent" | "pack" | "proof";
    id: string;
  } | null>(null);
  /** Ids that passed Test in this session (instant Promote unlock). */
  const [sessionTestOk, setSessionTestOk] = useState<Set<string>>(
    () => new Set(),
  );

  function markTestOk(id: string) {
    setSessionTestOk((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }

  useEffect(() => {
    if (tabParam === "agents" || tabParam === "packs" || tabParam === "proofs") {
      setTab(tabParam);
    }
  }, [tabParam]);

  function changeTab(next: Tab) {
    setTab(next);
    void navigate({ to: "/studio", search: { tab: next } });
  }

  // Agent form
  const [agentId, setAgentId] = useState("APXV-AGENT-OP-");
  const [agentName, setAgentName] = useState("");
  const [agentType, setAgentType] = useState("deterministic");
  const [agentDesc, setAgentDesc] = useState("");
  const [instruction, setInstruction] = useState(
    "# Instructions\n\nDescribe what this agent must do and the rules it must follow.\n",
  );
  const [knowledge, setKnowledge] = useState(
    "# Knowledge\n\nFacts and context this agent may use.\n",
  );

  // Pack form
  const [packId, setPackId] = useState("apxv-pack-");
  const [packName, setPackName] = useState("");
  const [packDesc, setPackDesc] = useState("");
  const [packAgents, setPackAgents] = useState("APXV-AGENT-001");
  const [rulesMd, setRulesMd] = useState(
    "# Rules\n\nGovernance rules for this pack.\n",
  );
  const [workflowMd, setWorkflowMd] = useState(
    "# Workflow\n\n1. Ingest\n2. Process\n3. Record\n",
  );
  const [knowledgeMd, setKnowledgeMd] = useState(
    "# Knowledge\n\nPack knowledge base.\n",
  );

  // Proof Profile form
  const [proofId, setProofId] = useState("APXV-PROOF-");
  const [proofName, setProofName] = useState("");
  const [proofDesc, setProofDesc] = useState("");
  const [intentMd, setIntentMd] = useState(
    "# Proof intent\n\nDescribe what this run must prove without revealing private data.\n",
  );
  const [selectedPredicates, setSelectedPredicates] = useState<string[]>(
    DEFAULT_PROOF_PREDICATES,
  );
  const [entityMin, setEntityMin] = useState(1);
  const [categories, setCategories] = useState("email, phone, ssn");
  const [requireAttest, setRequireAttest] = useState(false);

  const agentsQuery = useQuery({
    queryKey: ["studio", "agents"],
    queryFn: () => listStudioAgents(),
  });
  const packsQuery = useQuery({
    queryKey: ["studio", "packs"],
    queryFn: () => listStudioPacks(),
  });
  const proofsQuery = useQuery({
    queryKey: ["studio", "proofs"],
    queryFn: () => listStudioProofs(),
  });
  const catalogQuery = useQuery({
    queryKey: ["studio", "proofs", "catalog"],
    queryFn: () => listProofCatalog(),
  });
  const templatesQuery = useQuery({
    queryKey: ["studio", "proofs", "templates"],
    queryFn: () => listProofTemplates(),
  });
  const proofStatusQuery = useQuery({
    queryKey: ["studio", "proofs", "status"],
    queryFn: () => getProofStudioStatus(),
  });

  const saveAgentMutation = useMutation({
    mutationFn: () =>
      saveStudioAgent({
        id: agentId,
        name: agentName || agentId,
        description: agentDesc,
        agent_type: agentType,
        instruction_md: instruction,
        knowledge_md: knowledge,
      }),
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `Saved agent ${data.agent.id} — registered. Next: Test (runtime), then Promote to Workbench`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const testAgentMutation = useMutation({
    mutationFn: (id: string) => testStudioAgent(id),
    onSuccess: (data, id) => {
      setError(null);
      setMessage(
        data.ok
          ? `Agent test succeeded (${data.last_test?.final_status}) — ready to promote`
          : `Agent test finished: ${data.last_test?.final_status || "failed"}`,
      );
      if (data.ok) markTestOk(id);
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const promoteAgentMutation = useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) =>
      promoteStudioAgent(id, { force }),
    onSuccess: (data) => {
      setError(null);
      setForcePromote(null);
      setMessage(
        `Promoted ${data.agent.id} (${data.agent.maturity}) — available on Workbench shelf`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (err, vars) => {
      setMessage(null);
      setError(formatApiError(err));
      setForcePromote({ kind: "agent", id: vars.id });
    },
  });

  const savePackMutation = useMutation({
    mutationFn: () => {
      const agent_ids = packAgents
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      return saveStudioPack({
        id: packId,
        name: packName || packId,
        description: packDesc,
        rules_md: rulesMd,
        workflow_md: workflowMd,
        knowledge_md: knowledgeMd,
        agent_ids: agent_ids.length ? agent_ids : ["APXV-AGENT-001"],
      });
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `Saved pack ${data.pack.id} — next: Test (runtime), then Promote to Workbench`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const testPackMutation = useMutation({
    mutationFn: (id: string) => testStudioPack(id),
    onSuccess: (data, id) => {
      setError(null);
      setMessage(
        data.ok
          ? `Pack test succeeded — ready to promote`
          : `Pack test: ${data.last_test?.final_status || "failed"}`,
      );
      if (data.ok) markTestOk(id);
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const promotePackMutation = useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) =>
      promoteStudioPack(id, { force }),
    onSuccess: (data) => {
      setError(null);
      setForcePromote(null);
      setMessage(
        `Promoted pack ${data.pack.id} (${data.pack.maturity}) — on Workbench shelf`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
    },
    onError: (err, vars) => {
      setMessage(null);
      setError(formatApiError(err));
      setForcePromote({ kind: "pack", id: vars.id });
    },
  });

  const buildPredicatePayload = () => {
    return selectedPredicates.map((id) => {
      if (id === "ENTITY_COUNT_GTE") {
        return { id, params: { n: entityMin } };
      }
      if (id === "CATEGORY_INCLUDES") {
        return {
          id,
          params: {
            categories: categories
              .split(/[,\s]+/)
              .map((s) => s.trim())
              .filter(Boolean),
          },
        };
      }
      return { id };
    });
  };

  const saveProofMutation = useMutation({
    mutationFn: () =>
      saveStudioProof({
        id: proofId,
        name: proofName || proofId,
        description: proofDesc,
        intent_md: intentMd,
        predicates: buildPredicatePayload(),
        fail_closed: true,
        require_attest: requireAttest,
      }),
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `Saved proof profile ${data.proof.id} — next: Test (runtime), then Promote`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const testProofMutation = useMutation({
    mutationFn: (id: string) => testStudioProof(id),
    onSuccess: (data, id) => {
      setError(null);
      setMessage(
        data.ok
          ? `Proof test succeeded — claim holds. Ready to promote.`
          : `Proof test failed: ${data.last_test?.final_status || "failed"}`,
      );
      if (data.ok) markTestOk(id);
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const promoteProofMutation = useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) =>
      promoteStudioProof(id, { force }),
    onSuccess: (data) => {
      setError(null);
      setForcePromote(null);
      setMessage(
        `Promoted proof ${data.proof.id} (${data.proof.maturity}) — available on Workbench`,
      );
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err, vars) => {
      setMessage(null);
      setError(formatApiError(err));
      setForcePromote({ kind: "proof", id: vars.id });
    },
  });

  const fromTemplateMutation = useMutation({
    mutationFn: (templateId: string) =>
      saveStudioProofFromTemplate({ template_id: templateId }),
    onSuccess: (data) => {
      setError(null);
      setMessage(`Created ${data.proof.id} from template — review, Test, Promote`);
      setProofId(data.proof.id);
      setProofName(data.proof.name || "");
      setProofDesc(data.proof.description || "");
      setIntentMd(data.proof.intent_md || "");
      const preds = (data.proof.predicates || []).map((p) =>
        typeof p === "string" ? p : p.id,
      );
      setSelectedPredicates(preds);
      setRequireAttest(Boolean(data.proof.require_attest));
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const compileIntentMutation = useMutation({
    mutationFn: () =>
      compileProofIntent({
        intent_md: intentMd,
        proof_id: proofId.trim() || "APXV-PROOF-FROM-INTENT",
        name: proofName || "From intent",
      }),
    onSuccess: (data) => {
      setError(null);
      const preds = (data.predicates || []).map((p) =>
        typeof p === "string" ? p : p.id,
      );
      if (preds.length) setSelectedPredicates(preds);
      const warnings = (data.warnings || []).join(" ");
      setMessage(
        `Intent compiled (${data.source || "deterministic"}): ${preds.join(", ") || "none"}${
          warnings ? ` — ${warnings}` : ""
        }`,
      );
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const fromIntentMutation = useMutation({
    mutationFn: () =>
      saveStudioProofFromIntent({
        intent_md: intentMd,
        proof_id: proofId.trim() || "APXV-PROOF-FROM-INTENT",
        name: proofName || "From intent",
        prefer_universal: true,
      }),
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `Saved ${data.proof.id} from intent — Test, then Promote. Universal keys: ${
          proofStatusQuery.data?.universal_predicate_v1?.keys_available
            ? "ready"
            : "not yet"
        }`,
      );
      setProofId(data.proof.id);
      setProofName(data.proof.name || "");
      const preds = (data.proof.predicates || []).map((p) =>
        typeof p === "string" ? p : p.id,
      );
      if (preds.length) setSelectedPredicates(preds);
      void queryClient.invalidateQueries({ queryKey: ["studio"] });
    },
    onError: (err) => {
      setMessage(null);
      setError(formatApiError(err));
    },
  });

  const agents = agentsQuery.data?.agents ?? [];
  const packs = packsQuery.data?.packs ?? [];
  const proofs = proofsQuery.data?.proofs ?? [];
  const predicateCatalog: ProofPredicate[] =
    catalogQuery.data?.predicates ?? [];
  const templates = templatesQuery.data?.templates ?? [];

  const agentReady =
    sessionTestOk.has(agentId.trim()) ||
    studioTestPassed(agents.find((a) => a.id === agentId.trim())?.last_test);
  const packReady =
    sessionTestOk.has(packId.trim()) ||
    studioTestPassed(packs.find((p) => p.id === packId.trim())?.last_test);
  const proofReady =
    sessionTestOk.has(proofId.trim()) ||
    studioTestPassed(proofs.find((p) => p.id === proofId.trim())?.last_test);

  function canPromote(
    id: string,
    last?: { final_status?: string; ok?: boolean } | null,
  ) {
    return sessionTestOk.has(id) || studioTestPassed(last);
  }

  const togglePredicate = (id: string) => {
    setSelectedPredicates((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const claimPreview = useMemo(() => {
    if (!selectedPredicates.length) return "Select predicates to form a claim.";
    const parts = selectedPredicates.map((id) => {
      if (id === "ENTITY_COUNT_GTE") return `entity count ≥ ${entityMin}`;
      if (id === "CATEGORY_INCLUDES") return `categories include ${categories}`;
      const meta = predicateCatalog.find((p) => p.id === id);
      return meta?.title || id;
    });
    return `This run proves: ${parts.join("; ")}.`;
  }, [selectedPredicates, entityMin, categories, predicateCatalog]);

  return (
    <PageShell className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeader title="Studio" />
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
            Author Agents, Packs, and Proof Profiles; assemble them on the
            Workbench.{" "}
            <strong className="text-[hsl(var(--foreground))]">1 Save</strong> →{" "}
            <strong className="text-[hsl(var(--foreground))]">2 Test</strong> →{" "}
            <strong className="text-[hsl(var(--foreground))]">3 Promote</strong>.
            Proofs customize what is proven — not the circuits.
          </p>
          <ol className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-[hsl(var(--muted-foreground))]">
            <li className="rounded-full border border-[hsl(var(--divider-subtle))] px-2 py-0.5">
              1 · Save
            </li>
            <li className="rounded-full border border-[hsl(var(--divider-subtle))] px-2 py-0.5">
              2 · Test
            </li>
            <li className="rounded-full border border-[hsl(var(--divider-subtle))] px-2 py-0.5">
              3 · Promote
            </li>
          </ol>
        </div>
        <ActionGroup className="gap-2">
          <Button asChild variant="secondary" size="sm">
            <Link
              to="/workshop"
              search={{
                id: undefined,
                shelf:
                  tab === "packs"
                    ? "packs"
                    : tab === "proofs"
                      ? "proofs"
                      : "agents",
              }}
            >
              Open Workbench
            </Link>
          </Button>
          {tab === "proofs" ? (
            <Button asChild variant="secondary" size="sm">
              <Link to="/trust">Open Trust</Link>
            </Button>
          ) : null}
        </ActionGroup>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription className="space-y-2">
            <p>{error}</p>
            {forcePromote ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  const { kind, id } = forcePromote;
                  if (kind === "agent") {
                    promoteAgentMutation.mutate({ id, force: true });
                  } else if (kind === "pack") {
                    promotePackMutation.mutate({ id, force: true });
                  } else {
                    promoteProofMutation.mutate({ id, force: true });
                  }
                }}
              >
                Force promote {forcePromote.id}
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      {message ? (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={tab === "agents" ? "default" : "secondary"}
          onClick={() => changeTab("agents")}
        >
          Agents
        </Button>
        <Button
          size="sm"
          variant={tab === "packs" ? "default" : "secondary"}
          onClick={() => changeTab("packs")}
        >
          Packs
        </Button>
        <Button
          size="sm"
          variant={tab === "proofs" ? "default" : "secondary"}
          onClick={() => changeTab("proofs")}
        >
          Proofs
        </Button>
      </div>

      {tab === "agents" ? (
        <div className="grid gap-8 lg:grid-cols-2">
          <DataSurface className="space-y-4 rounded-xl border border-[hsl(var(--divider-subtle))] p-5">
            <h2 className="text-base font-semibold">New / edit Agent</h2>
            <div className="space-y-2">
              <Label htmlFor="agent-id">Agent id</Label>
              <Input
                id="agent-id"
                className="font-mono text-sm"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                placeholder="APXV-AGENT-OP-MY-AGENT"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-name">Name</Label>
              <Input
                id="agent-name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-type">Type</Label>
              <select
                id="agent-type"
                className="flex h-10 w-full rounded-md border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))] px-3 text-sm"
                value={agentType}
                onChange={(e) => setAgentType(e.target.value)}
              >
                <option value="deterministic">deterministic</option>
                <option value="agentic">agentic</option>
                <option value="hybrid">hybrid</option>
                <option value="tool">tool</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-desc">Description</Label>
              <Input
                id="agent-desc"
                value={agentDesc}
                onChange={(e) => setAgentDesc(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="instruction">instruction.md</Label>
              <Textarea
                id="instruction"
                rows={8}
                className="font-mono text-xs"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="knowledge">knowledge.md</Label>
              <Textarea
                id="knowledge"
                rows={5}
                className="font-mono text-xs"
                value={knowledge}
                onChange={(e) => setKnowledge(e.target.value)}
              />
            </div>
            <ActionGroup>
              <Button
                disabled={saveAgentMutation.isPending || !agentId.trim()}
                onClick={() => saveAgentMutation.mutate()}
              >
                Save & register
              </Button>
              <Button
                variant="secondary"
                disabled={testAgentMutation.isPending || !agentId.trim()}
                onClick={() => testAgentMutation.mutate(agentId.trim())}
              >
                Test (runtime)
              </Button>
              <Button
                variant="secondary"
                disabled={
                  promoteAgentMutation.isPending ||
                  !agentId.trim() ||
                  !agentReady
                }
                title={
                  !agentId.trim()
                    ? "Enter an agent id"
                    : !agentReady
                      ? "Run a successful Test first"
                      : "Promote to Workbench shelf"
                }
                onClick={() =>
                  promoteAgentMutation.mutate({ id: agentId.trim() })
                }
              >
                Promote
              </Button>
            </ActionGroup>
            {!agentReady && agentId.trim() ? (
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                Promote unlocks after a successful Test. If promote is rejected,
                use Force promote on the error banner.
              </p>
            ) : null}
          </DataSurface>

          <div className="space-y-3">
            <h2 className="text-base font-semibold">Your agents</h2>
            {agents.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No Studio agents yet. Save one to register it with the runtime.
              </p>
            ) : (
              agents.map((a: StudioAgent) => (
                <DataSurface
                  key={a.id}
                  className="space-y-2 rounded-lg border border-[hsl(var(--divider-subtle))] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-medium">{a.id}</span>
                    <Badge variant={a.promoted ? "success" : "secondary"}>
                      {a.maturity || (a.promoted ? "ready" : "draft")}
                    </Badge>
                    {a.last_test?.final_status ? (
                      <Badge
                        variant={
                          a.last_test.final_status === "succeeded"
                            ? "success"
                            : "destructive"
                        }
                      >
                        test: {a.last_test.final_status}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm">{a.name}</p>
                  <ActionGroup>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setAgentId(a.id);
                        setAgentName(a.name || "");
                        setAgentDesc(a.description || "");
                        setAgentType(a.agent_type || "deterministic");
                        setInstruction(a.instruction_md || "");
                        setKnowledge(a.knowledge_md || "");
                      }}
                    >
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => testAgentMutation.mutate(a.id)}
                    >
                      Test
                    </Button>
                    <Button
                      size="sm"
                      disabled={!canPromote(a.id, a.last_test)}
                      title={
                        canPromote(a.id, a.last_test)
                          ? "Promote to Workbench"
                          : "Run a successful Test first"
                      }
                      onClick={() => promoteAgentMutation.mutate({ id: a.id })}
                    >
                      Promote
                    </Button>
                  </ActionGroup>
                </DataSurface>
              ))
            )}
          </div>
        </div>
      ) : tab === "packs" ? (
        <div className="grid gap-8 lg:grid-cols-2">
          <DataSurface className="space-y-4 rounded-xl border border-[hsl(var(--divider-subtle))] p-5">
            <h2 className="text-base font-semibold">New / edit Pack</h2>
            <div className="space-y-2">
              <Label htmlFor="pack-id">Pack id</Label>
              <Input
                id="pack-id"
                className="font-mono text-sm"
                value={packId}
                onChange={(e) => setPackId(e.target.value)}
                placeholder="apxv-pack-my-kit"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-name">Name</Label>
              <Input
                id="pack-name"
                value={packName}
                onChange={(e) => setPackName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-desc">Description</Label>
              <Input
                id="pack-desc"
                value={packDesc}
                onChange={(e) => setPackDesc(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-agents">Bound agents</Label>
              <Input
                id="pack-agents"
                className="font-mono text-sm"
                value={packAgents}
                onChange={(e) => setPackAgents(e.target.value)}
                placeholder="APXV-AGENT-001"
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Comma-separated agent ids. Default uses the core redaction agent
                so pack profile tests run immediately.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rules">rules.md</Label>
              <Textarea
                id="rules"
                rows={5}
                className="font-mono text-xs"
                value={rulesMd}
                onChange={(e) => setRulesMd(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="workflow">workflow.md</Label>
              <Textarea
                id="workflow"
                rows={4}
                className="font-mono text-xs"
                value={workflowMd}
                onChange={(e) => setWorkflowMd(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-knowledge">knowledge.md</Label>
              <Textarea
                id="pack-knowledge"
                rows={4}
                className="font-mono text-xs"
                value={knowledgeMd}
                onChange={(e) => setKnowledgeMd(e.target.value)}
              />
            </div>
            <ActionGroup>
              <Button
                disabled={savePackMutation.isPending || !packId.trim()}
                onClick={() => savePackMutation.mutate()}
              >
                Save pack
              </Button>
              <Button
                variant="secondary"
                disabled={testPackMutation.isPending || !packId.trim()}
                onClick={() => testPackMutation.mutate(packId.trim())}
              >
                Test (runtime)
              </Button>
              <Button
                variant="secondary"
                disabled={
                  promotePackMutation.isPending || !packId.trim() || !packReady
                }
                title={
                  !packId.trim()
                    ? "Enter a pack id"
                    : !packReady
                      ? "Run a successful Test first"
                      : "Promote to Workbench shelf"
                }
                onClick={() =>
                  promotePackMutation.mutate({ id: packId.trim() })
                }
              >
                Promote
              </Button>
            </ActionGroup>
            {!packReady && packId.trim() ? (
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                Promote unlocks after a successful Test. Force promote is
                available if the gate still rejects.
              </p>
            ) : null}
          </DataSurface>

          <div className="space-y-3">
            <h2 className="text-base font-semibold">Your packs</h2>
            {packs.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No Studio packs yet. Example packs (redaction, document, AI
                governance) already prove the system on the Workbench.
              </p>
            ) : (
              packs.map((p: StudioPack) => (
                <DataSurface
                  key={p.id}
                  className="space-y-2 rounded-lg border border-[hsl(var(--divider-subtle))] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-medium">{p.id}</span>
                    <Badge variant={p.promoted ? "success" : "secondary"}>
                      {p.maturity || (p.promoted ? "ready" : "draft")}
                    </Badge>
                    {p.last_test?.final_status ? (
                      <Badge
                        variant={
                          p.last_test.final_status === "succeeded"
                            ? "success"
                            : "destructive"
                        }
                      >
                        test: {p.last_test.final_status}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm">{p.name}</p>
                  <ActionGroup>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setPackId(p.id);
                        setPackName(p.name || "");
                        setPackDesc(p.description || "");
                        setPackAgents(
                          (p.agents && p.agents.length
                            ? p.agents
                            : ["APXV-AGENT-001"]
                          ).join(", "),
                        );
                        setRulesMd(p.rules_md || "");
                        setWorkflowMd(p.workflow_md || "");
                        setKnowledgeMd(p.knowledge_md || "");
                      }}
                    >
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => testPackMutation.mutate(p.id)}
                    >
                      Test
                    </Button>
                    <Button
                      size="sm"
                      disabled={!canPromote(p.id, p.last_test)}
                      title={
                        canPromote(p.id, p.last_test)
                          ? "Promote to Workbench"
                          : "Run a successful Test first"
                      }
                      onClick={() => promotePackMutation.mutate({ id: p.id })}
                    >
                      Promote
                    </Button>
                  </ActionGroup>
                </DataSurface>
              ))
            )}
          </div>
        </div>
      ) : (
        <div className="grid gap-8 lg:grid-cols-2">
          <DataSurface className="space-y-4 rounded-xl border border-[hsl(var(--divider-subtle))] p-5">
            <h2 className="text-base font-semibold">New / edit Proof Profile</h2>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Select catalog predicates or type an intent. Claims map to the
              dual-track path and, when keys exist, real{" "}
              <code className="text-[10px]">universal-predicate-v1</code> Groth16
              proofs.
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Universal circuit keys:{" "}
              <strong className="text-[hsl(var(--foreground))]">
                {proofStatusQuery.data?.universal_predicate_v1?.keys_available
                  ? "available"
                  : "not found (run setup_universal_zk)"}
              </strong>
            </p>
            <div className="space-y-2">
              <Label htmlFor="proof-id">Proof id</Label>
              <Input
                id="proof-id"
                className="font-mono text-sm"
                value={proofId}
                onChange={(e) => setProofId(e.target.value)}
                placeholder="APXV-PROOF-MY-CLAIM"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="proof-name">Name</Label>
              <Input
                id="proof-name"
                value={proofName}
                onChange={(e) => setProofName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="proof-desc">Description</Label>
              <Input
                id="proof-desc"
                value={proofDesc}
                onChange={(e) => setProofDesc(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="intent">intent.md (type what you want to prove)</Label>
              <Textarea
                id="intent"
                rows={5}
                className="font-mono text-xs"
                value={intentMd}
                onChange={(e) => setIntentMd(e.target.value)}
                placeholder="Prove email and SSN were redacted, rules bound, and the run was attested."
              />
              <ActionGroup>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={compileIntentMutation.isPending || !intentMd.trim()}
                  onClick={() => compileIntentMutation.mutate()}
                >
                  Compile intent
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={fromIntentMutation.isPending || !intentMd.trim()}
                  onClick={() => fromIntentMutation.mutate()}
                >
                  Save from intent
                </Button>
              </ActionGroup>
            </div>
            <div className="space-y-2">
              <Label>Predicates (catalog)</Label>
              <div className="max-h-56 space-y-2 overflow-y-auto rounded-md border border-[hsl(var(--divider-subtle))] p-3">
                {predicateCatalog.length === 0 ? (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    Loading catalog…
                  </p>
                ) : (
                  predicateCatalog.map((p) => (
                    <label
                      key={p.id}
                      className="flex cursor-pointer items-start gap-2 text-sm"
                    >
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={selectedPredicates.includes(p.id)}
                        onChange={() => togglePredicate(p.id)}
                      />
                      <span>
                        <span className="font-medium">{p.title || p.id}</span>
                        <span className="mt-0.5 block font-mono text-[11px] text-[hsl(var(--muted-foreground))]">
                          {p.id}
                          {p.requires_zk ? " · requires ZK attest" : ""}
                        </span>
                      </span>
                    </label>
                  ))
                )}
              </div>
            </div>
            {selectedPredicates.includes("ENTITY_COUNT_GTE") ? (
              <div className="space-y-2">
                <Label htmlFor="entity-min">Entity count ≥ N</Label>
                <Input
                  id="entity-min"
                  type="number"
                  min={0}
                  value={entityMin}
                  onChange={(e) => setEntityMin(Number(e.target.value) || 0)}
                />
              </div>
            ) : null}
            {selectedPredicates.includes("CATEGORY_INCLUDES") ? (
              <div className="space-y-2">
                <Label htmlFor="cats">Categories (comma-separated)</Label>
                <Input
                  id="cats"
                  value={categories}
                  onChange={(e) => setCategories(e.target.value)}
                  placeholder="email, phone, ssn"
                />
              </div>
            ) : null}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={requireAttest}
                onChange={(e) => setRequireAttest(e.target.checked)}
              />
              Require full ZK attest when this profile runs
            </label>
            <DataSurface className="bg-[hsl(var(--muted)/0.3)] p-3 text-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                Claim preview
              </div>
              <p className="mt-1">{claimPreview}</p>
            </DataSurface>
            <ActionGroup>
              <Button
                disabled={
                  saveProofMutation.isPending ||
                  !proofId.trim() ||
                  selectedPredicates.length === 0
                }
                title={
                  selectedPredicates.length === 0
                    ? "Select at least one predicate"
                    : !proofId.trim()
                      ? "Enter a proof profile id"
                      : "Save this proof profile"
                }
                onClick={() => saveProofMutation.mutate()}
              >
                Save profile
              </Button>
              <Button
                variant="secondary"
                disabled={testProofMutation.isPending || !proofId.trim()}
                onClick={() => testProofMutation.mutate(proofId.trim())}
              >
                Test (runtime)
              </Button>
              <Button
                variant="secondary"
                disabled={
                  promoteProofMutation.isPending ||
                  !proofId.trim() ||
                  !proofReady
                }
                title={
                  !proofId.trim()
                    ? "Enter a proof profile id"
                    : !proofReady
                      ? "Run a successful Test first"
                      : "Promote to Workbench shelf"
                }
                onClick={() =>
                  promoteProofMutation.mutate({ id: proofId.trim() })
                }
              >
                Promote
              </Button>
            </ActionGroup>
            {!proofReady && proofId.trim() ? (
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                Promote unlocks after a successful Test. Force promote is
                available if the gate still rejects.
              </p>
            ) : null}
            {templates.length > 0 ? (
              <div className="space-y-2 border-t border-[hsl(var(--divider-subtle))] pt-4">
                <Label>Start from template</Label>
                <div className="flex flex-wrap gap-2">
                  {templates.map((t) => (
                    <Button
                      key={t.id}
                      size="sm"
                      variant="secondary"
                      disabled={fromTemplateMutation.isPending}
                      onClick={() => fromTemplateMutation.mutate(t.id)}
                    >
                      {t.name || t.id}
                    </Button>
                  ))}
                </div>
              </div>
            ) : null}
          </DataSurface>

          <div className="space-y-3">
            <h2 className="text-base font-semibold">Your proof profiles</h2>
            {proofs.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No proof profiles yet. Use a template or select predicates and
                Save. After promote, attach{" "}
                <code className="text-xs">proof_profile</code> on Workbench
                pipelines.
              </p>
            ) : (
              proofs.map((p: StudioProof) => (
                <DataSurface
                  key={p.id}
                  className="space-y-2 rounded-lg border border-[hsl(var(--divider-subtle))] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-medium">{p.id}</span>
                    <Badge variant={p.promoted ? "success" : "secondary"}>
                      {p.maturity || (p.promoted ? "ready" : "draft")}
                    </Badge>
                    {p.last_test?.final_status || p.last_test?.ok != null ? (
                      <Badge
                        variant={
                          p.last_test.final_status === "succeeded" ||
                          p.last_test.ok
                            ? "success"
                            : "destructive"
                        }
                      >
                        test:{" "}
                        {p.last_test.final_status ||
                          (p.last_test.ok ? "succeeded" : "failed")}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm">{p.name}</p>
                  {p.claim_english ? (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {p.claim_english}
                    </p>
                  ) : null}
                  <ActionGroup>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setProofId(p.id);
                        setProofName(p.name || "");
                        setProofDesc(p.description || "");
                        setIntentMd(p.intent_md || "");
                        setSelectedPredicates(
                          (p.predicates || []).map((x) =>
                            typeof x === "string" ? x : x.id,
                          ),
                        );
                        setRequireAttest(Boolean(p.require_attest));
                        const ent = (p.predicates || []).find(
                          (x) =>
                            typeof x !== "string" && x.id === "ENTITY_COUNT_GTE",
                        );
                        if (ent && typeof ent !== "string" && ent.params?.n != null) {
                          setEntityMin(Number(ent.params.n));
                        }
                        const cat = (p.predicates || []).find(
                          (x) =>
                            typeof x !== "string" &&
                            x.id === "CATEGORY_INCLUDES",
                        );
                        if (
                          cat &&
                          typeof cat !== "string" &&
                          Array.isArray(cat.params?.categories)
                        ) {
                          setCategories(
                            (cat.params.categories as string[]).join(", "),
                          );
                        }
                      }}
                    >
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => testProofMutation.mutate(p.id)}
                    >
                      Test
                    </Button>
                    <Button
                      size="sm"
                      disabled={!canPromote(p.id, p.last_test)}
                      title={
                        canPromote(p.id, p.last_test)
                          ? "Promote to Workbench"
                          : "Run a successful Test first"
                      }
                      onClick={() => promoteProofMutation.mutate({ id: p.id })}
                    >
                      Promote
                    </Button>
                  </ActionGroup>
                </DataSurface>
              ))
            )}
          </div>
        </div>
      )}
    </PageShell>
  );
}
