import {
  exportPipeline,
  getPipeline,
  listAgents,
  listPacks,
  runCompositionPipeline,
  savePipeline,
  validatePipeline,
  type PipelineDocument,
  type PipelineStep,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  Checkbox,
  Input,
  Label,
  PageToolbar,
  SectionHeader,
  Select,
  Skeleton,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";
import {
  CORE_AGENT_USES,
  defaultStep,
  downloadText,
  emptyPipeline,
  moveStep,
  SAMPLE_PIPELINE_INPUT,
} from "../lib/workshop-pipeline";

export function WorkshopComposerPage() {
  const { id: pipelineId } = useSearch({ from: "/shell/workshop/composer" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [doc, setDoc] = useState<PipelineDocument>(() => emptyPipeline());
  const [inputText, setInputText] = useState(SAMPLE_PIPELINE_INPUT);
  const [attest, setAttest] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadQuery = useQuery({
    queryKey: ["pipelines", "detail", pipelineId],
    queryFn: () => getPipeline(pipelineId!),
    enabled: Boolean(pipelineId),
  });

  useEffect(() => {
    if (loadQuery.data?.pipeline) {
      setDoc(loadQuery.data.pipeline);
      setAttest(Boolean(loadQuery.data.pipeline.defaults?.attest));
      setLoadError(null);
    }
  }, [loadQuery.data]);

  useEffect(() => {
    if (loadQuery.isError) {
      setLoadError(formatApiError(loadQuery.error));
    }
  }, [loadQuery.isError, loadQuery.error]);

  const agentsQuery = useQuery({
    queryKey: ["agents", "composer"],
    queryFn: () => listAgents({ limit: 100 }),
  });
  const packsQuery = useQuery({
    queryKey: ["packs", "composer"],
    queryFn: () => listPacks(),
  });

  const usesOptions = useMemo(() => {
    const opts = [...CORE_AGENT_USES.map((o) => ({ value: o.uses, label: o.label }))];
    for (const agent of agentsQuery.data?.items ?? []) {
      const uses = `agent:${agent.id}`;
      if (!opts.some((o) => o.value === uses)) {
        opts.push({
          value: uses,
          label: `${agent.id} — ${agent.name || agent.agent_type}`,
        });
      }
    }
    for (const pack of packsQuery.data?.packs ?? []) {
      const uses = `pack:${pack.id}`;
      if (!opts.some((o) => o.value === uses)) {
        opts.push({ value: uses, label: `Pack — ${pack.name || pack.id}` });
      }
    }
    return opts;
  }, [agentsQuery.data, packsQuery.data]);

  const updateStep = (index: number, patch: Partial<PipelineStep>) => {
    setDoc((prev) => {
      const steps = prev.steps.map((s, i) =>
        i === index ? { ...s, ...patch } : s,
      );
      return { ...prev, steps };
    });
  };

  const validateMutation = useMutation({
    mutationFn: () => validatePipeline(doc),
    onSuccess: (result) => {
      setErrors(result.errors ?? []);
      setWarnings(result.warnings ?? []);
      if (result.ok && result.pipeline) {
        setDoc(result.pipeline);
        setMessage("Pipeline is valid");
      } else {
        setMessage(null);
      }
    },
    onError: (err) => setErrors([formatApiError(err)]),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const v = await validatePipeline(doc);
      if (!v.ok || !v.pipeline) {
        throw new Error(v.errors.join("; ") || "Validation failed");
      }
      return savePipeline({
        pipeline: {
          ...v.pipeline,
          defaults: {
            ...(v.pipeline.defaults ?? {}),
            attest,
            on_step_failure: v.pipeline.defaults?.on_step_failure ?? "stop",
          },
        },
        format: "yaml",
        overwrite: true,
      });
    },
    onSuccess: (data) => {
      setErrors([]);
      setMessage(`Saved ${data.pipeline.id}`);
      setDoc(data.pipeline);
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      void navigate({
        to: "/workshop/composer",
        search: { id: data.pipeline.id },
      });
    },
    onError: (err) => setErrors([formatApiError(err)]),
  });

  const runMutation = useMutation({
    mutationFn: async () => {
      const saved = await saveMutation.mutateAsync();
      return runCompositionPipeline({
        pipeline_id: saved.pipeline.id,
        input_text: inputText,
        attest,
        async: true,
      });
    },
    onSuccess: (result) => {
      setErrors([]);
      if (result.mode === "queued") {
        const jobId = String(result.job_id ?? result.id ?? "");
        if (jobId) {
          notifyPipelineQueued(queryClient, jobId, {
            pipeline_id: doc.id,
          });
          void navigate({ to: "/jobs", search: { id: jobId } });
          return;
        }
      }
      setMessage("Run complete — open Jobs for history");
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (err) => setErrors([formatApiError(err)]),
  });

  const exportMutation = useMutation({
    mutationFn: async () => {
      await saveMutation.mutateAsync();
      return exportPipeline(doc.id, "yaml");
    },
    onSuccess: (data) => {
      downloadText(`${data.pipeline_id}.yaml`, data.content, "text/yaml");
      setMessage(`Exported ${data.pipeline_id}`);
    },
    onError: (err) => setErrors([formatApiError(err)]),
  });

  if (pipelineId && loadQuery.isLoading) {
    return (
      <PageShell>
        <SectionHeader title="Composer" />
        <Skeleton className="h-40 w-full" />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <SectionHeader title="Pipeline composer" />
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Ordered list of steps — order is run order. Same Pipeline Spec as CLI and
        API.
      </p>
      <PageToolbar>
        <ActionGroup className="flex-wrap">
            <Button variant="secondary" asChild>
              <Link to="/workshop/library">Library</Link>
            </Button>
            <Button
              variant="secondary"
              disabled={validateMutation.isPending}
              onClick={() => validateMutation.mutate()}
            >
              Validate
            </Button>
            <Button
              variant="secondary"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              Save
            </Button>
            <Button
              variant="secondary"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate()}
            >
              Export YAML
            </Button>
            <Button
              disabled={runMutation.isPending}
              onClick={() => runMutation.mutate()}
            >
              Save & run
            </Button>
          </ActionGroup>
      </PageToolbar>

      {loadError ? (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      ) : null}
      {errors.length > 0 ? (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            <ul className="list-disc pl-4">
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}
      {warnings.length > 0 ? (
        <Alert className="mb-4">
          <AlertDescription>
            Warnings: {warnings.join("; ")}
          </AlertDescription>
        </Alert>
      ) : null}
      {message ? (
        <Alert className="mb-4">
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="pipe-id">Pipeline id</Label>
          <Input
            id="pipe-id"
            value={doc.id}
            onChange={(e) => setDoc((d) => ({ ...d, id: e.target.value.trim() }))}
            className="font-mono text-sm"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="pipe-name">Name</Label>
          <Input
            id="pipe-name"
            value={doc.name}
            onChange={(e) => setDoc((d) => ({ ...d, name: e.target.value }))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="pipe-ver">Version</Label>
          <Input
            id="pipe-ver"
            value={doc.version}
            onChange={(e) => setDoc((d) => ({ ...d, version: e.target.value }))}
          />
        </div>
        <div className="flex items-end gap-2 pb-2">
          <Checkbox
            id="pipe-attest"
            checked={attest}
            onChange={(e) => setAttest(e.target.checked)}
            label="End-of-pipeline attest (optional)"
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="pipe-desc">Description</Label>
          <Textarea
            id="pipe-desc"
            rows={2}
            value={doc.description ?? ""}
            onChange={(e) =>
              setDoc((d) => ({ ...d, description: e.target.value }))
            }
          />
        </div>
      </div>

      <SectionHeader title="Steps" className="mb-1" />
      <p className="mb-3 text-sm text-[hsl(var(--muted-foreground))]">
        Building blocks run top to bottom. Reorder with Move up / Move down.
      </p>
      <div className="mb-4 space-y-3">
        {doc.steps.map((step, index) => (
          <div
            key={`${step.id}-${index}`}
            className="space-y-3 rounded-lg border border-[hsl(var(--divider-subtle))] p-3"
          >
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label>Step id</Label>
                <Input
                  value={step.id}
                  className="font-mono text-sm"
                  onChange={(e) =>
                    updateStep(index, { id: e.target.value.trim() })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label>Name</Label>
                <Input
                  value={step.name}
                  onChange={(e) => updateStep(index, { name: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Uses</Label>
                <Select
                  value={step.uses}
                  onChange={(e) => updateStep(index, { uses: e.target.value })}
                >
                  {usesOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                  {!usesOptions.some((o) => o.value === step.uses) ? (
                    <option value={step.uses}>{step.uses}</option>
                  ) : null}
                </Select>
              </div>
            </div>
            <ActionGroup>
              <Button
                size="sm"
                variant="secondary"
                disabled={index === 0}
                onClick={() =>
                  setDoc((d) => ({
                    ...d,
                    steps: moveStep(d.steps, index, -1),
                  }))
                }
              >
                Move up
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={index === doc.steps.length - 1}
                onClick={() =>
                  setDoc((d) => ({
                    ...d,
                    steps: moveStep(d.steps, index, 1),
                  }))
                }
              >
                Move down
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={doc.steps.length <= 1}
                onClick={() =>
                  setDoc((d) => ({
                    ...d,
                    steps: d.steps.filter((_, i) => i !== index),
                  }))
                }
              >
                Remove
              </Button>
            </ActionGroup>
          </div>
        ))}
      </div>
      <Button
        variant="secondary"
        className="mb-8"
        onClick={() =>
          setDoc((d) => ({ ...d, steps: [...d.steps, defaultStep(d.steps)] }))
        }
      >
        Add step
      </Button>

      <SectionHeader title="Run input" className="mb-1" />
      <p className="mb-3 text-sm text-[hsl(var(--muted-foreground))]">
        Sample text for this composition. Results appear under Jobs with a run trace.
      </p>
      <Textarea
        rows={4}
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        className="mb-4 font-mono text-sm"
      />
    </PageShell>
  );
}
