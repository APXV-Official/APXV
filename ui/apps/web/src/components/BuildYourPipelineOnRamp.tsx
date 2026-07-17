import { ActionGroup, Button, Panel, PanelBody, PanelHeader } from "@apxv/ui";
import { Link } from "@tanstack/react-router";
import { Layers, Sparkles } from "lucide-react";
import { PACK_TUTORIAL_URL, PIPELINE_COMPOSER_V15_NOTE } from "../lib/pack-studio";

export function BuildYourPipelineOnRamp() {
  return (
    <Panel className="border border-[hsl(var(--divider-subtle))] bg-gradient-to-br from-[hsl(var(--surface-elevated))]/80 to-[hsl(var(--surface))]">
      <PanelHeader
        title="Build your pipeline"
        description="Author a governed agent pack without editing Python in the repo — template, governance, activate, test."
        actions={
          <Sparkles
            className="h-5 w-5 text-[hsl(var(--muted-foreground))]"
            aria-hidden
          />
        }
      />
      <PanelBody className="space-y-4 pt-0">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {PIPELINE_COMPOSER_V15_NOTE}
        </p>
        <ActionGroup className="flex-wrap">
          <Button asChild className="gap-2">
            <Link to="/packs" search={{ wizard: "1", pack: undefined }}>
              <Layers className="h-4 w-4" aria-hidden />
              Start pack wizard
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/packs" search={{ wizard: undefined, pack: undefined }}>
              Open pack studio
            </Link>
          </Button>
          <Button variant="link" size="sm" asChild>
            <a href={PACK_TUTORIAL_URL} target="_blank" rel="noopener noreferrer">
              BUILD-YOUR-FIRST-PACK guide
            </a>
          </Button>
        </ActionGroup>
      </PanelBody>
    </Panel>
  );
}