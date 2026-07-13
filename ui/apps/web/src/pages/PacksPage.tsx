import {
  activatePack,
  clonePack,
  createPack,
  getActivePack,
  getPack,
  listPacks,
  runPipeline,
  type PackInfo,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  PageToolbar,
  DataSurface,
  Input,
  Label,
  SectionHeader,
  Select,
  Skeleton,
  Textarea,
  Checkbox,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { QueryState } from "../components/QueryState";
import {
  SelectableListBadge,
  SelectableListItem,
} from "../components/SelectableListItem";
import { PackStudioOnRamp } from "../components/PackStudioOnRamp";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";
import {
  defaultQuickCloneId,
  REFERENCE_PACK_ID,
  type PackTemplate,
} from "../lib/pack-studio";

function packKind(pack: PackInfo): string {
  const id = pack.id.toLowerCase();
  if (id.includes("document")) return "document";
  if (id.includes("ai")) return "ai";
  if (id.includes("reference")) return "reference";
  return "custom";
}

function defaultPackId(slug: string) {
  const clean = slug
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return clean ? `apxv-pack-${clean}` : "";
}

export function PacksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showClone, setShowClone] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [slugInput, setSlugInput] = useState("");
  const [descInput, setDescInput] = useState("");
  const [template, setTemplate] = useState<"reference" | "minimal">("reference");
  const [cloneSlug, setCloneSlug] = useState("");
  const [cloneName, setCloneName] = useState("");
  const [confirmActivate, setConfirmActivate] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const packsQuery = useQuery({
    queryKey: ["packs"],
    queryFn: () => listPacks(),
  });

  const activePackQuery = useQuery({
    queryKey: ["packs", "active"],
    queryFn: () => getActivePack(),
  });

  const activePackId = activePackQuery.data?.active?.pack_id ?? null;
  const packs = packsQuery.data?.packs ?? [];
  const activeId = selectedId ?? packs[0]?.id ?? null;

  const detailQuery = useQuery({
    queryKey: ["packs", activeId],
    queryFn: () => getPack(activeId!),
    enabled: Boolean(activeId),
  });

  const packIdPreview = useMemo(
    () => defaultPackId(slugInput || nameInput),
    [slugInput, nameInput],
  );

  const clonePackIdPreview = useMemo(
    () => defaultPackId(cloneSlug || cloneName),
    [cloneSlug, cloneName],
  );

  const createMutation = useMutation({
    mutationFn: () =>
      createPack({
        pack_id: packIdPreview,
        name: nameInput.trim(),
        description: descInput.trim(),
        template,
      }),
    onSuccess: (data) => {
      setActionError(null);
      setShowCreate(false);
      setNameInput("");
      setSlugInput("");
      setDescInput("");
      setSelectedId(data.pack.pack_id);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      setActionMessage(`Pack created: ${data.pack.pack_id}`);
    },
    onError: (err) => setActionError(formatApiError(err)),
  });

  const activateMutation = useMutation({
    mutationFn: (pack: PackInfo) =>
      activatePack(pack.id, {
        confirm: !pack.official,
        activated_by: "operator-console",
      }),
    onSuccess: (data) => {
      setActionError(null);
      setConfirmActivate(false);
      setActionMessage(`Active pack: ${data.pack_id}`);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      void queryClient.invalidateQueries({ queryKey: ["packs", "active"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["governance"] });
    },
    onError: (err) => setActionError(formatApiError(err)),
  });

  const quickCloneReferenceMutation = useMutation({
    mutationFn: () => {
      const packId = defaultQuickCloneId();
      return clonePack(REFERENCE_PACK_ID, {
        pack_id: packId,
        name: "My Redaction Pack",
        description: "Clone of Reference Redaction Pack — customize governance and agents",
      });
    },
    onSuccess: (data) => {
      setActionError(null);
      setShowClone(false);
      setSelectedId(data.pack.pack_id);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      setActionMessage(
        `Reference pack duplicated as ${data.pack.pack_id}. Set active, then edit governance.`,
      );
    },
    onError: (err) => setActionError(formatApiError(err)),
  });

  const cloneMutation = useMutation({
    mutationFn: (pack: PackInfo) =>
      clonePack(pack.id, {
        pack_id: clonePackIdPreview,
        name: cloneName.trim() || clonePackIdPreview,
        description: `Clone of ${pack.name}`,
      }),
    onSuccess: (data) => {
      setActionError(null);
      setShowClone(false);
      setCloneSlug("");
      setCloneName("");
      setSelectedId(data.pack.pack_id);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      setActionMessage(`Pack cloned: ${data.pack.pack_id}`);
    },
    onError: (err) => setActionError(formatApiError(err)),
  });

  const runMutation = useMutation({
    mutationFn: async (pack: PackInfo) => {
      setRunMessage(null);
      setActionError(null);
      const kind = packKind(pack);
      const body: Parameters<typeof runPipeline>[0] = {
        pack: pack.id,
        attest: true,
        async: true,
      };
      if (kind === "document") {
        throw new Error(
          "Document pack needs a file — open Pipeline and upload a file to run.",
        );
      }
      body.input_text =
        "Contact: jane@example.com, phone (555) 123-4567, SSN 123-45-6789.";
      return runPipeline(body);
    },
    onSuccess: (result, pack) => {
      if (result.mode === "queued" && result.job_id) {
        notifyPipelineQueued(queryClient, result.job_id, {
          pack: pack.id,
          attest: true,
        });
        setRunMessage(`Job queued: ${result.job_id}`);
        void navigate({ to: "/jobs", search: { id: result.job_id } });
      } else {
        void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      }
    },
    onError: (err) => setActionError(formatApiError(err)),
  });

  const activePack = packs.find((p) => p.id === activeId);
  const isActivePack = Boolean(activePackId && activePack?.id === activePackId);
  const needsConfirm = Boolean(activePack && !activePack.official);
  const hasCustomPack = packs.some((p) => !p.official);

  function openCreateForm(nextTemplate: PackTemplate) {
    setShowCreate(true);
    setTemplate(nextTemplate);
    setNameInput(
      nextTemplate === "reference" ? "My Agent Pack" : "My Minimal Pack",
    );
    setSlugInput(nextTemplate === "reference" ? "my-agent-pack" : "my-minimal-pack");
    setDescInput(
      nextTemplate === "reference"
        ? "Custom pack scaffolded from the reference redaction template"
        : "Empty governance stubs — add rules and agents yourself",
    );
    setActionError(null);
  }

  return (
    <PageShell wide className="space-y-10">
      <PackStudioOnRamp
        onDuplicateReference={() => quickCloneReferenceMutation.mutate()}
        onCreateFromTemplate={openCreateForm}
        duplicatePending={quickCloneReferenceMutation.isPending}
        showGettingStarted={!hasCustomPack || showCreate}
      />

      <PageToolbar>
        <ActionGroup>
          <Button variant="link" size="sm" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Cancel" : "Create pack"}
          </Button>
          <Button variant="link" size="sm" asChild>
            <Link to="/agents">Agent registry</Link>
          </Button>
          <Button variant="link" size="sm" asChild>
            <Link to="/pipeline">Pipeline runner</Link>
          </Button>
        </ActionGroup>
      </PageToolbar>

      {activePackQuery.data?.active && (
        <Alert variant="success">
          <AlertTitle>Active pack</AlertTitle>
          <AlertDescription>
            {activePackQuery.data.pack?.name ?? activePackQuery.data.active.pack_id}{" "}
            <span className="font-mono text-xs">
              ({activePackQuery.data.active.pack_id})
            </span>
          </AlertDescription>
        </Alert>
      )}

      {actionError && (
        <Alert variant="destructive">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}
      {actionMessage && (
        <Alert variant="success">
          <AlertDescription>{actionMessage}</AlertDescription>
        </Alert>
      )}
      {runMessage && (
        <Alert variant="success">
          <AlertDescription>{runMessage}</AlertDescription>
        </Alert>
      )}

      {showCreate && (
        <section className="space-y-4 border-b border-[hsl(var(--divider))] pb-6">
          <SectionHeader title="New agent pack" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Scaffolds a pack under governance-libraries/ with agents and governance stubs.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="pack-name">Display name</Label>
              <Input
                id="pack-name"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder="My Redaction Agent"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-slug">URL slug</Label>
              <Input
                id="pack-slug"
                value={slugInput}
                onChange={(e) => setSlugInput(e.target.value)}
                placeholder="my-redaction-agent"
              />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Pack id: <span className="font-mono">{packIdPreview || "—"}</span>
              </p>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="pack-desc">Description</Label>
              <Textarea
                id="pack-desc"
                rows={2}
                value={descInput}
                onChange={(e) => setDescInput(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pack-template">Template</Label>
              <Select
                id="pack-template"
                className="w-full"
                value={template}
                onChange={(e) =>
                  setTemplate(e.target.value as "reference" | "minimal")
                }
              >
                <option value="reference">Reference (full redaction pipeline)</option>
                <option value="minimal">Minimal (empty governance stubs)</option>
              </Select>
            </div>
            <div className="flex items-end sm:col-span-2">
              <ActionGroup>
                <Button
                  disabled={
                    !nameInput.trim() || !packIdPreview || createMutation.isPending
                  }
                  onClick={() => createMutation.mutate()}
                >
                  {createMutation.isPending ? "Creating…" : "Create pack"}
                </Button>
              </ActionGroup>
            </div>
          </div>
        </section>
      )}

      <div className="grid min-w-0 gap-8 xl:grid-cols-12 xl:gap-10">
        <section className="min-w-0 space-y-4 xl:col-span-4">
          <SectionHeader
            title="Installed packs"
            action={
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                {packs.length}
              </span>
            }
          />
          <DataSurface>
            <QueryState
              isLoading={packsQuery.isLoading}
              isError={packsQuery.isError}
              error={packsQuery.error}
              isEmpty={!packsQuery.isLoading && packs.length === 0}
              emptyTitle="No packs found"
              emptyDescription="Use Duplicate reference pack above, or create from a template."
            >
              <div className="divide-y divide-[hsl(var(--divider-subtle))]">
                {packs.map((pack) => (
                  <SelectableListItem
                    key={pack.id}
                    selected={activeId === pack.id}
                    onClick={() => setSelectedId(pack.id)}
                    title={pack.name}
                    subtitle={pack.id}
                    badge={
                      <>
                        <SelectableListBadge>{packKind(pack)}</SelectableListBadge>
                        {pack.id === activePackId && (
                          <SelectableListBadge variant="success">Active</SelectableListBadge>
                        )}
                      </>
                    }
                  />
                ))}
              </div>
            </QueryState>
          </DataSurface>
        </section>

        <section className="min-w-0 space-y-5 border-t border-[hsl(var(--divider))] pt-6 xl:col-span-8 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0">
          <SectionHeader title={activePack?.name ?? "Pack detail"} />
          {activePack?.description && activePack.description !== ">-" && (
            <p className="text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
              {activePack.description}
            </p>
          )}

          {detailQuery.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}

          {activePack && (
            <>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-[hsl(var(--muted-foreground))]">
                <span>Version {activePack.version}</span>
                {activePack.official && <span>· Official</span>}
                {activePack.requires_apxv1 && (
                  <span>· Requires runtime {activePack.requires_apxv1}</span>
                )}
                {activePack.path && <span>· {activePack.path}</span>}
              </div>

              {detailQuery.data?.readme_excerpt && (
                <pre className="max-h-48 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm whitespace-pre-wrap">
                  {detailQuery.data.readme_excerpt}
                </pre>
              )}

              {activePack.id === REFERENCE_PACK_ID && (
                <p className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                  This is the official reference pack. Use{" "}
                  <strong>Duplicate reference pack</strong> at the top to make an
                  editable copy without changing the built-in pack.
                </p>
              )}

              {detailQuery.data?.agents && detailQuery.data.agents.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Agent chain</p>
                  <ol className="list-decimal space-y-1 pl-5 text-sm text-[hsl(var(--muted-foreground))]">
                    {detailQuery.data.agents.map((agent) => (
                      <li key={agent.id}>
                        <span className="font-mono text-xs">{agent.id}</span>
                        {agent.type && (
                          <span className="ml-2 text-[hsl(var(--caption))]">
                            ({agent.type})
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {needsConfirm && !isActivePack && (
                <Checkbox
                  id="confirm-activate"
                  checked={confirmActivate}
                  onChange={(e) => setConfirmActivate(e.target.checked)}
                  label="Confirm activation of non-official pack"
                />
              )}

              <ActionGroup>
                <Button
                  onClick={() => activePack && activateMutation.mutate(activePack)}
                  disabled={
                    activateMutation.isPending ||
                    isActivePack ||
                    (needsConfirm && !confirmActivate)
                  }
                >
                  {isActivePack
                    ? "Active pack"
                    : activateMutation.isPending
                      ? "Activating…"
                      : "Set active"}
                </Button>
                <Button
                  onClick={() => activePack && runMutation.mutate(activePack)}
                  disabled={runMutation.isPending || !activePack}
                >
                  {runMutation.isPending ? "Running…" : "Run pack (sample input)"}
                </Button>
                {activePack.id === REFERENCE_PACK_ID ? (
                  <Button
                    variant="link"
                    disabled={quickCloneReferenceMutation.isPending}
                    onClick={() => quickCloneReferenceMutation.mutate()}
                  >
                    {quickCloneReferenceMutation.isPending
                      ? "Duplicating…"
                      : "Duplicate reference pack"}
                  </Button>
                ) : (
                  <Button
                    variant="link"
                    onClick={() => {
                      setShowClone((v) => !v);
                      setCloneName(`${activePack.name} Copy`);
                      setCloneSlug(`${packKind(activePack)}-copy`);
                    }}
                  >
                    {showClone ? "Cancel clone" : "Clone pack"}
                  </Button>
                )}
                <Button
                  variant="link"
                  onClick={() => {
                    sessionStorage.setItem("apxv.selectedPackId", activePack.id);
                    void navigate({ to: "/pipeline" });
                  }}
                >
                  Configure in pipeline
                </Button>
                <Button variant="link" asChild>
                  <Link
                    to="/governance"
                    search={{ tab: "specs", proposal: undefined }}
                  >
                    Governance studio
                  </Link>
                </Button>
              </ActionGroup>

              {showClone && (
                <div className="grid gap-4 rounded-xl border border-[hsl(var(--divider))] p-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="clone-name">Clone name</Label>
                    <Input
                      id="clone-name"
                      value={cloneName}
                      onChange={(e) => setCloneName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="clone-slug">Clone slug</Label>
                    <Input
                      id="clone-slug"
                      value={cloneSlug}
                      onChange={(e) => setCloneSlug(e.target.value)}
                    />
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                      New id:{" "}
                      <span className="font-mono">{clonePackIdPreview || "—"}</span>
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <Button
                      disabled={
                        !clonePackIdPreview ||
                        cloneMutation.isPending ||
                        clonePackIdPreview === activePack.id
                      }
                      onClick={() => cloneMutation.mutate(activePack)}
                    >
                      {cloneMutation.isPending ? "Cloning…" : "Clone pack"}
                    </Button>
                  </div>
                </div>
              )}

              {packKind(activePack) === "document" && (
                <Alert variant="warning">
                  <AlertTitle>Document pack</AlertTitle>
                  <AlertDescription>
                    Upload .txt or .json files in the Pipeline runner — sample text
                    run is not supported.
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}
        </section>
      </div>
    </PageShell>
  );
}