import type { ReactNode } from "react";

function renderInline(text: string) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-[hsl(var(--muted))] px-1 py-0.5 font-mono text-xs"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

export function MarkdownViewer({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length === 0) return;
    elements.push(
      <ul
        key={`list-${elements.length}`}
        className="mb-3 list-disc space-y-1 pl-5 text-sm"
      >
        {listItems.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  }

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      listItems.push(trimmed.slice(2));
      continue;
    }
    flushList();

    if (trimmed.startsWith("### ")) {
      elements.push(
        <h3 key={elements.length} className="mb-2 mt-4 text-sm font-semibold">
          {renderInline(trimmed.slice(4))}
        </h3>,
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h2 key={elements.length} className="mb-2 mt-4 text-base font-semibold">
          {renderInline(trimmed.slice(3))}
        </h2>,
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h1 key={elements.length} className="mb-3 text-lg font-semibold">
          {renderInline(trimmed.slice(2))}
        </h1>,
      );
    } else if (trimmed === "") {
      elements.push(<div key={elements.length} className="h-2" />);
    } else {
      elements.push(
        <p key={elements.length} className="mb-2 text-sm leading-relaxed">
          {renderInline(line)}
        </p>,
      );
    }
  }
  flushList();

  return (
    <div className="prose-invert max-w-none text-[hsl(var(--foreground))]">
      {elements}
    </div>
  );
}