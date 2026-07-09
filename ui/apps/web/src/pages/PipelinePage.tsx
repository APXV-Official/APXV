import {
  createUpload,
  getActivePack,
  getOllamaStatus,
  getPackAgents,
  listPacks,
  runPipeline,
  type PackInfo,
  type PipelineRunRequest,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Checkbox,
  Input,
  Label,
  SectionHeader,
  Select,
  StatusDot,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";

function packKind(pack: PackInfo): "reference" | "document" | "ai" | "custom" {
  const id = pack.id.toLowerCase();
  if (id.includes("document")) return "document";
  if (id.includes("ai")) return "ai";
  if (id.includes("reference")) return "reference";
  return "custom";
}

function disabledReason(
  packs: PackInfo[],
  pack: PackInfo | undefined,
  kind: string,
  selectedFiles: File[],
  inputText: string,
  loading: boolean,
  packsError: boolean,
): string | null {
  if (loading) return "Loading agent packs…";
  if (packsError) return "Cannot load packs — check API connection.";
  if (packs.length === 0) return "No agent packs installed on this runtime.";
  if (!pack) return "Select an agent pack.";
  if (kind === "document" && selectedFiles.length === 0) {
    return "Document pack requires a file upload (.txt or .json).";
  }
  if (selectedFiles.length === 0 && !inputText.trim()) {
    return "Provide input text or upload a file.";
  }
  return null;
}

export function PipelinePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const packsQuery = useQuery({
    queryKey: ["packs"],
    queryFn: () => listPacks(),
  });

  const activePackQuery = useQuery({
    queryKey: ["packs", "active"],
    queryFn: () => getActivePack(),
  });

  const ollamaQuery = useQuery({
    queryKey: ["ollama"],
    queryFn: () => getOllamaStatus(),
    staleTime: 30_000,
  });

  const packs = packsQuery.data?.packs ?? [];
  const [selectedPackId, setSelectedPackId] = useState<string>("");
  const [inputText, setInputText] = useState(
    "Contact: jane@example.com, SSN 123-45-6789",
  );
  const [attest, setAttest] = useState(true);
  const [useLlm, setUseLlm] = useState(false);
  const [llmModel, setLlmModel] = useState("");
  const [uploadLabel, setUploadLabel] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!packs.length) return;
    const stored = sessionStorage.getItem("apxv.selectedPackId");
    if (stored && packs.some((p) => p.id === stored)) {
      setSelectedPackId(stored);
      sessionStorage.removeItem("apxv.selectedPackId");
      return;
    }
    if (!selectedPackId) {
      const ref =
        packs.find((p) => p.id.toLowerCase().includes("reference")) ?? packs[0];
      setSelectedPackId(ref.id);
    }
  }, [packs, selectedPackId]);

  const activePack = useMemo(
    () => packs.find((p) => p.id === selectedPackId) ?? packs[0],
    [packs, selectedPackId],
  );

  const chainQuery = useQuery({
    queryKey: ["packs", activePack?.id, "agents"],
    queryFn: () => getPackAgents(activePack!.id),
    enabled: Boolean(activePack?.id),
  });

  const kind = activePack ? packKind(activePack) : "reference";
  const showLlm = kind === "ai" || useLlm;
  const blockReason = disabledReason(
    packs,
    activePack,
    kind,
    selectedFiles,
    inputText,
    packsQuery.isLoading,
    packsQuery.isError,
  );

  const runMutation = useMutation({
    mutationFn: async () => {
      setError(null);
      setResultMessage(null);

      if (!activePack) throw new Error("Select an agent pack.");
      if (kind === "document" && selectedFiles.length === 0) {
        throw new Error("Document pack requires a file upload (.txt or .json).");
      }

      let uploadId: string | undefined;
      if (selectedFiles.length > 0) {
        const session = await createUpload(selectedFiles, uploadLabel);
        uploadId = session.upload_id;
      }

      const body: PipelineRunRequest = {
        pack: activePack.id,
        attest,
        async: true,
      };

      if (uploadId) {
        body.input_files = [uploadId];
      } else if (inputText.trim()) {
        body.input_text = inputText.trim();
      } else {
        throw new Error("Provide input text or upload a file.");
      }

      if (showLlm) {
        body.llm = {
          backend: ollamaQuery.data?.reachable ? "ollama" : "simulated",
          model: llmModel || ollamaQuery.data?.models?.[0]?.name || "qwen2.5",
          max_latency_ms: 120_000,
        };
      }

      return runPipeline(body);
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      if (result.mode === "queued" && result.job_id) {
        setResultMessage(`Job queued: ${result.job_id}`);
        void navigate({ to: "/jobs", search: { id: result.job_id } });
      } else {
        setResultMessage(result.message ?? "Pipeline complete.");
      }
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const canRun = !runMutation.isPending && blockReason === null;

  return (
    <PageShell className="mx-auto max-w-3xl space-y-10">
      <SectionHeader title="Pipeline runner" />

      {packsQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Cannot load agent packs</AlertTitle>
          <AlertDescription>{formatApiError(packsQuery.error)}</AlertDescription>
        </Alert>
      )}

      <form
        className="space-y-10"
        onSubmit={(e) => {
          e.preventDefault();
          if (canRun) runMutation.mutate();
        }}
      >
        <section className="space-y-3">
          <Label htmlFor="pack">Agent pack</Label>
          <Select
            id="pack"
            className="w-full"
            value={selectedPackId || packs[0]?.id || ""}
            onChange={(e) => setSelectedPackId(e.target.value)}
            disabled={packsQuery.isLoading || packs.length === 0}
          >
            {packs.map((pack) => (
              <option key={pack.id} value={pack.id}>
                {pack.name} ({pack.id})
              </option>
            ))}
          </Select>
          {activePack?.description && activePack.description !== ">-" && (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {activePack.description}
            </p>
          )}
          {activePackQuery.data?.active?.pack_id === activePack?.id && (
            <p className="text-sm text-[hsl(var(--primary))]">Active pack for governance</p>
          )}
        </section>

        {chainQuery.data && chainQuery.data.agents.length > 0 && (
          <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
            <SectionHeader title="Agent chain" />
            <ol className="space-y-2">
              {chainQuery.data.agents.map((agent, index) => (
                <li
                  key={agent.id}
                  className="flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-3 text-sm"
                >
                  <span className="font-mono text-xs text-[hsl(var(--caption))]">
                    {index + 1}.
                  </span>
                  <span className="font-medium">{agent.name}</span>
                  <span className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
                    {agent.id}
                  </span>
                  {agent.declared_type && (
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      ({agent.declared_type})
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}

        <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
          <Label htmlFor="input-text">
            Input text
            {kind === "document" && (
              <span className="ml-2 font-normal text-[hsl(var(--muted-foreground))]">
                (not used when uploading files)
              </span>
            )}
          </Label>
          <Textarea
            id="input-text"
            rows={6}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={kind === "document"}
            placeholder="Text to process through the selected pack…"
          />
        </section>

        <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
          <Label htmlFor="file-upload">
            Upload files {kind === "document" ? "(required)" : "(optional)"}
          </Label>
          <Input
            id="file-upload"
            type="file"
            accept=".txt,.json"
            multiple
            onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
          />
          <Input
            placeholder="Upload label (optional)"
            value={uploadLabel}
            onChange={(e) => setUploadLabel(e.target.value)}
          />
          {selectedFiles.length > 0 && (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {selectedFiles.length} file(s) selected — uploaded when you run.
            </p>
          )}
        </section>

        <section className="space-y-4 border-t border-[hsl(var(--divider))] pt-8">
          <Checkbox
            id="attest"
            checked={attest}
            onChange={(e) => setAttest(e.target.checked)}
            label="Attest output (ZK proofs)"
          />
          {kind !== "ai" && (
            <Checkbox
              id="use-llm"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              label="Enable LLM review"
            />
          )}
        </section>

        {showLlm && (
          <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
            <div className="flex items-center gap-3">
              <Label>LLM config</Label>
              <span className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                <StatusDot
                  tone={ollamaQuery.data?.reachable ? "success" : "warning"}
                />
                {ollamaQuery.data?.reachable ? "Ollama reachable" : "Simulated"}
              </span>
            </div>
            <Select
              className="w-full"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            >
              <option value="">Default model</option>
              {(ollamaQuery.data?.models ?? []).map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </Select>
          </section>
        )}

        <div className="space-y-4 border-t border-[hsl(var(--divider))] pt-8">
          {!canRun && blockReason && !runMutation.isPending && (
            <Alert variant="warning">
              <AlertDescription>{blockReason}</AlertDescription>
            </Alert>
          )}

          <ActionGroup>
            <Button type="submit" disabled={!canRun}>
              {runMutation.isPending ? "Queuing job…" : "Run pipeline"}
            </Button>
          </ActionGroup>

          {resultMessage && (
            <Alert variant="success">
              <AlertDescription>{resultMessage}</AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Run failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      </form>
    </PageShell>
  );
}