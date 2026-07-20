import {
  deletePipeline,
  exportPipeline,
  getPipelineTemplate,
  importPipeline,
  listPipelineTemplates,
  listPipelines,
  runCompositionPipeline,
  savePipeline,
  type PipelineListItem,
  type PipelineTemplateInfo,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  EmptyState,
  PageToolbar,
  SectionHeader,
  Skeleton,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";
import {
  downloadText,
  emptyPipeline,
  SAMPLE_PIPELINE_INPUT,
} from "../lib/workshop-pipeline";

export function WorkshopLibraryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [importText, setImportText] = useState("");
  const [showImport, setShowImport] = useState(false);

  const localQuery = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => listPipelines(),
  });
  const templatesQuery = useQuery({
    queryKey: ["pipelines", "templates"],
    queryFn: () => listPipelineTemplates(),
  });

  const installTemplate = useMutation({
    mutationFn: async (template: PipelineTemplateInfo) => {
      const detail = await getPipelineTemplate(template.id);
      if (detail.pipeline) {
        return savePipeline({
          pipeline: detail.pipeline,
          format: "yaml",
          overwrite: true,
        });
      }
      return importPipeline({
        content: detail.content,
        format: "auto",
        overwrite: true,
      });
    },
    onSuccess: (data) => {
      setError(null);
      const id =
        "pipeline" in data && data.pipeline
          ? data.pipeline.id
          : "document" in data
            ? data.document.id
            : "";
      setMessage(`Installed example pipeline ${id}`);
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      void navigate({
        to: "/workshop",
        search: { id: id || undefined, shelf: "library" },
      });
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const runMutation = useMutation({
    mutationFn: (id: string) =>
      runCompositionPipeline({
        pipeline_id: id,
        input_text: SAMPLE_PIPELINE_INPUT,
        async: true,
      }),
    onSuccess: (result) => {
      setError(null);
      if (result.mode === "queued") {
        const jobId = String(result.job_id ?? result.id ?? "");
        if (jobId) {
          notifyPipelineQueued(queryClient, jobId, {
            pipeline_id: result.pipeline_id,
          });
          void navigate({ to: "/jobs", search: { id: jobId } });
          return;
        }
      }
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setMessage("Pipeline run finished");
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const exportMutation = useMutation({
    mutationFn: async (id: string) => exportPipeline(id, "yaml"),
    onSuccess: (data) => {
      downloadText(`${data.pipeline_id}.yaml`, data.content, "text/yaml");
      setMessage(`Exported ${data.pipeline_id}`);
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const importMutation = useMutation({
    mutationFn: () =>
      importPipeline({ content: importText, format: "auto", overwrite: true }),
    onSuccess: (data) => {
      setError(null);
      setMessage(`Imported ${data.document.id}`);
      setShowImport(false);
      setImportText("");
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      void navigate({
        to: "/workshop",
        search: { id: data.document.id, shelf: "library" },
      });
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePipeline(id),
    onSuccess: (_, id) => {
      setMessage(`Deleted ${id}`);
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const locals = localQuery.data?.pipelines ?? [];
  const templates = templatesQuery.data?.templates ?? [];

  return (
    <PageShell>
      <SectionHeader title="Pipeline library" />
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Saved and example compositions. Open the Workbench board to build.
      </p>
      <PageToolbar>
        <ActionGroup className="flex-wrap">
            <Button
              onClick={() =>
                void navigate({
                  to: "/workshop",
                  search: { id: undefined, shelf: "library" },
                })
              }
            >
              Open Workbench
            </Button>
            <Button variant="secondary" onClick={() => setShowImport((v) => !v)}>
              Import YAML/JSON
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/studio" search={{ tab: "packs" }}>
                Studio · Packs
              </Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link
                to="/workshop"
                search={{ id: undefined, shelf: "packs" }}
              >
                Workbench · Packs shelf
              </Link>
            </Button>
          </ActionGroup>
      </PageToolbar>

      {error ? (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {message ? (
        <Alert className="mb-4">
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}

      {showImport ? (
        <div className="mb-6 space-y-3 rounded-lg border border-[hsl(var(--divider-subtle))] p-4">
          <SectionHeader title="Import pipeline" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Paste a Pipeline Spec v0.1 document (YAML or JSON). Same contract as the CLI.
          </p>
          <Textarea
            rows={10}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder="apiVersion: apxv.pipeline/v0.1 …"
            className="font-mono text-xs"
          />
          <ActionGroup>
            <Button
              disabled={!importText.trim() || importMutation.isPending}
              onClick={() => importMutation.mutate()}
            >
              Validate and import
            </Button>
            <Button variant="ghost" onClick={() => setShowImport(false)}>
              Cancel
            </Button>
          </ActionGroup>
        </div>
      ) : null}

      <section className="mb-8 space-y-3">
        <SectionHeader title="Example pipelines" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Demo compositions (maturity Example). Install into your local library to edit and run.
        </p>
        {templatesQuery.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : templates.length === 0 ? (
          <EmptyState
            title="No example pipelines found"
            description="Ship examples under examples/pipelines/ in the APXV tree, or create a new pipeline."
          />
        ) : (
          <ul className="space-y-2">
            {templates.map((t) => (
              <li
                key={t.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-[hsl(var(--divider-subtle))] px-3 py-3"
              >
                <div className="min-w-0">
                  <p className="font-medium">{t.name || t.id}</p>
                  <p className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
                    {t.id}
                    {t.step_count != null ? ` · ${t.step_count} steps` : ""}
                    {" · Example"}
                  </p>
                  {t.description ? (
                    <p className="mt-1 line-clamp-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {t.description}
                    </p>
                  ) : null}
                </div>
                <ActionGroup>
                  <Button
                    size="sm"
                    disabled={installTemplate.isPending}
                    onClick={() => installTemplate.mutate(t)}
                  >
                    Install & edit
                  </Button>
                </ActionGroup>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <SectionHeader title="Local pipelines" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Stored under managed/pipelines on this instance.
        </p>
        {localQuery.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : locals.length === 0 ? (
          <EmptyState
            title="No local pipelines yet"
            description="Install an example above, import a file, or create a new composition."
            action={
              <Button
                onClick={() => {
                  const doc = emptyPipeline();
                  void savePipeline({ pipeline: doc, overwrite: true }).then(
                    () => {
                      void queryClient.invalidateQueries({
                        queryKey: ["pipelines"],
                      });
                      void navigate({
                        to: "/workshop",
                        search: { id: doc.id, shelf: "library" },
                      });
                    },
                  );
                }}
              >
                Create blank pipeline
              </Button>
            }
          />
        ) : (
          <ul className="space-y-2">
            {locals.map((p: PipelineListItem) => (
              <li
                key={p.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-[hsl(var(--divider-subtle))] px-3 py-3"
              >
                <div className="min-w-0">
                  <p className="font-medium">{p.name || p.id}</p>
                  <p className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
                    {p.id}
                    {p.version ? ` · v${p.version}` : ""}
                    {p.step_count != null ? ` · ${p.step_count} steps` : ""}
                    {p.valid === false ? " · invalid" : ""}
                  </p>
                </div>
                <ActionGroup className="flex-wrap">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      void navigate({
                        to: "/workshop",
                        search: { id: p.id, shelf: "library" },
                      })
                    }
                  >
                    Open on board
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      void navigate({
                        to: "/workshop/composer",
                        search: { id: p.id },
                      })
                    }
                  >
                    List composer
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      void navigate({
                        to: "/workshop/canvas",
                        search: { id: p.id },
                      })
                    }
                  >
                    Canvas
                  </Button>
                  <Button
                    size="sm"
                    disabled={!p.valid || runMutation.isPending}
                    onClick={() => runMutation.mutate(p.id)}
                  >
                    Run
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={exportMutation.isPending}
                    onClick={() => exportMutation.mutate(p.id)}
                  >
                    Export
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      if (
                        window.confirm(
                          `Delete local pipeline ${p.id}? This cannot be undone.`,
                        )
                      ) {
                        deleteMutation.mutate(p.id);
                      }
                    }}
                  >
                    Delete
                  </Button>
                </ActionGroup>
              </li>
            ))}
          </ul>
        )}
      </section>
    </PageShell>
  );
}
