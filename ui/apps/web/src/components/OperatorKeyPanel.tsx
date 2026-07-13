import { ActionGroup, Button } from "@apxv/ui";
import type { DiscoveredOperatorKey } from "../lib/operator-key-discovery";
import { copyToClipboard } from "../lib/format-id";

interface OperatorKeyPanelProps {
  operatorKey: DiscoveredOperatorKey | null;
  loadError: string | null;
  busy?: boolean;
  onUseKey?: (key: string) => void;
  onSaveKey?: () => void;
  saveMessage?: string | null;
  showSave?: boolean;
  onReload?: () => void;
}

export function OperatorKeyPanel({
  operatorKey,
  loadError,
  busy = false,
  onUseKey,
  onSaveKey,
  saveMessage,
  showSave = false,
  onReload,
}: OperatorKeyPanelProps) {
  async function handleCopy() {
    if (!operatorKey) return;
    const ok = await copyToClipboard(operatorKey.key);
    if (!ok && onUseKey) {
      onUseKey(operatorKey.key);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-[hsl(var(--divider-subtle))] px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-base font-medium">Discovered operator key</p>
        <ActionGroup>
          {onReload && (
            <Button
              type="button"
              variant="link"
              className="h-auto px-0 py-0 text-xs"
              onClick={() => onReload()}
              disabled={busy}
            >
              Reload
            </Button>
          )}
          <Button
            type="button"
            variant="link"
            className="h-auto px-0 py-0 text-xs"
            onClick={() => void handleCopy()}
            disabled={!operatorKey || busy}
          >
            Copy
          </Button>
          {showSave && onSaveKey && (
            <Button
              type="button"
              variant="link"
              className="h-auto px-0 py-0 text-xs"
              onClick={() => void onSaveKey()}
              disabled={!operatorKey || busy}
            >
              Save to file
            </Button>
          )}
        </ActionGroup>
      </div>

      {operatorKey ? (
        <>
          <code className="block break-all rounded-md bg-[hsl(var(--surface-elevated))] px-3 py-2 font-mono text-sm">
            {operatorKey.key}
          </code>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            From <span className="font-mono">{operatorKey.file_path}</span>
          </p>
          {onUseKey && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={busy}
              onClick={() => onUseKey(operatorKey.key)}
            >
              Use this key
            </Button>
          )}
        </>
      ) : (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {loadError ??
            "No OPERATOR-KEY-*.txt found yet. Run bootstrap/setup, or paste the key below."}
        </p>
      )}

      {saveMessage && (
        <p className="text-xs text-[hsl(var(--muted-foreground))]">{saveMessage}</p>
      )}
    </div>
  );
}