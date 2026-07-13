import { ActionGroup, Button, Panel, PanelBody, PanelHeader } from "@apxv/ui";
import { BookOpen, Copy, Plus } from "lucide-react";
import {
  PACK_CATALOG_URL,
  PACK_TUTORIAL_URL,
  type PackTemplate,
} from "../lib/pack-studio";

interface PackStudioOnRampProps {
  onDuplicateReference: () => void;
  onCreateFromTemplate: (template: PackTemplate) => void;
  duplicatePending?: boolean;
  showGettingStarted?: boolean;
}

export function PackStudioOnRamp({
  onDuplicateReference,
  onCreateFromTemplate,
  duplicatePending = false,
  showGettingStarted = true,
}: PackStudioOnRampProps) {
  if (!showGettingStarted) return null;

  return (
    <Panel className="border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface-elevated))]/40">
      <PanelHeader
        title="Build your first pack"
        description="Duplicate the reference redaction pack, edit governance rules, then activate and run."
      />
      <PanelBody className="space-y-4 pt-0">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-[hsl(var(--muted-foreground))]">
          <li>
            <strong className="font-medium text-[hsl(var(--foreground))]">
              Duplicate
            </strong>{" "}
            the reference pack (or create from a template)
          </li>
          <li>
            <strong className="font-medium text-[hsl(var(--foreground))]">
              Customize
            </strong>{" "}
            rules, workflows, and agents in Governance + pack folder
          </li>
          <li>
            <strong className="font-medium text-[hsl(var(--foreground))]">
              Activate
            </strong>{" "}
            your pack and run a pipeline job
          </li>
        </ol>

        <ActionGroup className="flex-wrap">
          <Button
            onClick={onDuplicateReference}
            disabled={duplicatePending}
            className="gap-2"
          >
            <Copy className="h-4 w-4" aria-hidden />
            {duplicatePending ? "Duplicating…" : "Duplicate reference pack"}
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            onClick={() => onCreateFromTemplate("reference")}
          >
            <Plus className="h-4 w-4" aria-hidden />
            New from reference template
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            onClick={() => onCreateFromTemplate("minimal")}
          >
            <Plus className="h-4 w-4" aria-hidden />
            New minimal pack
          </Button>
          <Button variant="link" size="sm" asChild>
            <a href={PACK_TUTORIAL_URL} target="_blank" rel="noopener noreferrer">
              <BookOpen className="mr-1 inline h-4 w-4" aria-hidden />
              Tutorial: BUILD-YOUR-FIRST-PACK
            </a>
          </Button>
          <Button variant="link" size="sm" asChild>
            <a href={PACK_CATALOG_URL} target="_blank" rel="noopener noreferrer">
              Pack catalog
            </a>
          </Button>
        </ActionGroup>
      </PanelBody>
    </Panel>
  );
}