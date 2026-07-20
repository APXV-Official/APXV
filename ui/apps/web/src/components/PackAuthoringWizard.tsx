import {
  activatePack,
  createPack,
  runPipeline,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  Input,
  Label,
  Panel,
  PanelBody,
  PanelHeader,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";
import {
  packIdFromSlug,
  PACK_TUTORIAL_URL,
  PIPELINE_COMPOSER_V15_NOTE,
  validatePackId,
  WIZARD_STEPS,
  type PackTemplate,
} from "../lib/pack-studio";

const SAMPLE_INPUT =
  "Contact: jane@example.com, phone (555) 123-4567, SSN 123-45-6789.";

interface PackAuthoringWizardProps {
  onClose?: () => void;
  initialTemplate?: PackTemplate;
}

export function PackAuthoringWizard({
  onClose,
  initialTemplate = "reference",
}: PackAuthoringWizardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [stepIndex, setStepIndex] = useState(0);
  const [template, setTemplate] = useState<PackTemplate>(initialTemplate);
  const [name, setName] = useState(
    initialTemplate === "reference" ? "My Agent Pack" : "My Minimal Pack",
  );
  const [slug, setSlug] = useState(
    initialTemplate === "reference" ? "my-agent-pack" : "my-minimal-pack",
  );
  const [description, setDescription] = useState(
    initialTemplate === "reference"
      ? "Custom pack from the reference redaction template"
      : "Minimal governance stubs — add rules and agents yourself",
  );
  const [createdPackId, setCreatedPackId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const step = WIZARD_STEPS[stepIndex];
  const packId = useMemo(() => packIdFromSlug(slug || name), [slug, name]);
  const packIdError = validatePackId(packId);

  const createMutation = useMutation({
    mutationFn: () =>
      createPack({
        pack_id: packId,
        name: name.trim(),
        description: description.trim(),
        template,
      }),
    onSuccess: (data) => {
      setError(null);
      setCreatedPackId(data.pack.pack_id);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      setSuccess(`Pack created: ${data.pack.pack_id}`);
      setStepIndex((i) => Math.min(i + 1, WIZARD_STEPS.length - 1));
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) =>
      activatePack(id, { confirm: true, activated_by: "pack-wizard" }),
    onSuccess: (data) => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["packs"] });
      void queryClient.invalidateQueries({ queryKey: ["packs", "active"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["governance"] });
      setSuccess(`Active pack: ${data.pack_id}`);
      setStepIndex((i) => Math.min(i + 1, WIZARD_STEPS.length - 1));
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const testRunMutation = useMutation({
    mutationFn: (id: string) =>
      runPipeline({
        pack: id,
        input_text: SAMPLE_INPUT,
        attest: true,
        async: true,
      }),
    onSuccess: (result, packId) => {
      setError(null);
      if (result.mode === "queued" && result.job_id) {
        notifyPipelineQueued(queryClient, result.job_id, {
          pack: packId,
          attest: true,
        });
        void navigate({ to: "/jobs", search: { id: result.job_id } });
      }
    },
    onError: (err) => setError(formatApiError(err)),
  });

  const activePackId = createdPackId ?? packId;

  function goBack() {
    setError(null);
    setStepIndex((i) => Math.max(0, i - 1));
  }

  function goNext() {
    setError(null);
    setSuccess(null);
    const current = WIZARD_STEPS[stepIndex].id;

    if (current === "template") {
      setStepIndex(1);
      return;
    }
    if (current === "identity") {
      if (!name.trim() || packIdError) {
        setError(packIdError ?? "Display name is required.");
        return;
      }
      if (createdPackId) {
        setStepIndex(2);
        return;
      }
      createMutation.mutate();
      return;
    }
    if (current === "governance") {
      setStepIndex(3);
      return;
    }
    if (current === "activate") {
      if (!activePackId) {
        setError("Create the pack first.");
        return;
      }
      activateMutation.mutate(activePackId);
      return;
    }
  }

  return (
    <Panel
      className="border border-[hsl(var(--primary))]/20"
      data-testid="pack-authoring-wizard"
      aria-label="Pack authoring wizard"
    >
      <PanelHeader
        title="Pack authoring wizard"
        description={PIPELINE_COMPOSER_V15_NOTE}
        actions={
          onClose ? (
            <Button variant="link" size="sm" onClick={onClose}>
              Close wizard
            </Button>
          ) : null
        }
      />
      <PanelBody className="space-y-6 pt-0">
        <nav aria-label="Wizard progress" className="flex flex-wrap gap-2">
          {WIZARD_STEPS.map((s, i) => (
            <span
              key={s.id}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                i === stepIndex
                  ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                  : i < stepIndex
                    ? "bg-[hsl(var(--surface-elevated))] text-[hsl(var(--foreground))]"
                    : "bg-[hsl(var(--surface-elevated))]/60 text-[hsl(var(--muted-foreground))]"
              }`}
            >
              {i < stepIndex ? (
                <Check className="h-3 w-3" aria-hidden />
              ) : (
                <span className="tabular-nums">{i + 1}</span>
              )}
              {s.label}
            </span>
          ))}
        </nav>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {success && step.id !== "test" && (
          <Alert variant="success">
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        {step.id === "template" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => {
                setTemplate("reference");
                setName("My Agent Pack");
                setSlug("my-agent-pack");
                setDescription(
                  "Custom pack from the reference redaction template",
                );
              }}
              className={`rounded-xl border p-4 text-left transition-colors ${
                template === "reference"
                  ? "border-[hsl(var(--primary))] bg-[hsl(var(--surface-elevated))]"
                  : "border-[hsl(var(--divider))] hover:bg-[hsl(var(--surface-elevated))]/50"
              }`}
            >
              <p className="font-medium">Reference template</p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                Full redaction pipeline — rules, workflow, agents, and demo
                hooks copied from the official reference pack.
              </p>
            </button>
            <button
              type="button"
              onClick={() => {
                setTemplate("minimal");
                setName("My Minimal Pack");
                setSlug("my-minimal-pack");
                setDescription(
                  "Minimal governance stubs — add rules and agents yourself",
                );
              }}
              className={`rounded-xl border p-4 text-left transition-colors ${
                template === "minimal"
                  ? "border-[hsl(var(--primary))] bg-[hsl(var(--surface-elevated))]"
                  : "border-[hsl(var(--divider))] hover:bg-[hsl(var(--surface-elevated))]/50"
              }`}
            >
              <p className="font-medium">Minimal template</p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                Empty governance stubs and a single custom agent entry — best
                when you already know your workflow shape.
              </p>
            </button>
          </div>
        )}

        {step.id === "identity" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="wizard-pack-name">Display name</Label>
              <Input
                id="wizard-pack-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Redaction Pack"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wizard-pack-slug">URL slug</Label>
              <Input
                id="wizard-pack-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="my-redaction-pack"
              />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Pack id:{" "}
                <span className="font-mono">{packId || "—"}</span>
                {packIdError && (
                  <span className="mt-1 block text-[hsl(var(--destructive))]">
                    {packIdError}
                  </span>
                )}
              </p>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="wizard-pack-desc">Description</Label>
              <Textarea
                id="wizard-pack-desc"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>
        )}

        {step.id === "governance" && (
          <div className="space-y-4 text-sm text-[hsl(var(--muted-foreground))]">
            <p>
              Your pack lives under{" "}
              <span className="font-mono text-xs">
                governance-libraries/{activePackId}/
              </span>
              . Edit rules, workflows, and knowledge before activation, or use
              governed proposals after activation.
            </p>
            <ol className="list-decimal space-y-2 pl-5">
              <li>
                Open <strong className="text-[hsl(var(--foreground))]">Governance studio</strong> to
                review active specs or propose changes.
              </li>
              <li>
                Activation snapshots governance into{" "}
                <span className="font-mono text-xs">managed/</span> for the
                runtime — required before pipeline jobs use your pack.
              </li>
            </ol>
            <ActionGroup>
              <Button variant="secondary" asChild>
                <Link
                  to="/governance"
                  search={{ tab: "specs", proposal: undefined }}
                  onClick={() => onClose?.()}
                >
                  Open governance studio
                </Link>
              </Button>
              <Button variant="link" size="sm" asChild>
                <a href={PACK_TUTORIAL_URL} target="_blank" rel="noopener noreferrer">
                  Authoring guide
                </a>
              </Button>
            </ActionGroup>
          </div>
        )}

        {step.id === "activate" && (
          <div className="space-y-3 text-sm">
            <p className="text-[hsl(var(--muted-foreground))]">
              Set <span className="font-mono">{activePackId}</span> as the
              active pack. Non-official packs require confirmation — the wizard
              handles that for you.
            </p>
            {createdPackId && (
              <p className="text-[hsl(var(--muted-foreground))]">
                Pack scaffold is on disk. Activation wires governance into the
                runtime and updates the agent registry.
              </p>
            )}
          </div>
        )}

        {step.id === "test" && (
          <div className="space-y-4 text-sm">
            <p className="text-[hsl(var(--muted-foreground))]">
              Queue a sample reference-style pipeline job with attestation on{" "}
              <span className="font-mono">{activePackId}</span>. Document packs
              need a file upload — use the Pipeline runner instead.
            </p>
            <ActionGroup>
              <Button
                onClick={() => testRunMutation.mutate(activePackId)}
                disabled={testRunMutation.isPending || !activePackId}
              >
                {testRunMutation.isPending
                  ? "Queueing test job…"
                  : "Run test job (sample input)"}
              </Button>
              <Button variant="link" asChild>
                <Link
                  to="/workshop"
                  search={{ id: undefined, shelf: "packs" }}
                >
                  Open Workbench
                </Link>
              </Button>
            </ActionGroup>
          </div>
        )}

        <ActionGroup className="border-t border-[hsl(var(--divider-subtle))] pt-4">
          <Button
            variant="secondary"
            className="gap-1"
            onClick={goBack}
            disabled={
              stepIndex === 0 ||
              createMutation.isPending ||
              activateMutation.isPending
            }
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
            Back
          </Button>
          {step.id !== "test" && (
            <Button
              className="gap-1"
              onClick={goNext}
              disabled={
                createMutation.isPending ||
                activateMutation.isPending ||
                (step.id === "identity" && (!name.trim() || Boolean(packIdError)))
              }
            >
              {step.id === "identity" && !createdPackId
                ? createMutation.isPending
                  ? "Creating pack…"
                  : "Create pack & continue"
                : step.id === "activate"
                  ? activateMutation.isPending
                    ? "Activating…"
                    : "Activate pack"
                  : "Continue"}
              <ChevronRight className="h-4 w-4" aria-hidden />
            </Button>
          )}
          {step.id === "test" && onClose && (
            <Button variant="link" onClick={onClose}>
              Done — browse packs
            </Button>
          )}
        </ActionGroup>
      </PanelBody>
    </Panel>
  );
}

/** Sample input reused by pack detail run actions. */
export function samplePackRunInput(): string {
  return SAMPLE_INPUT;
}