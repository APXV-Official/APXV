export type DiffLineKind = "same" | "add" | "remove" | "change";

export interface DiffLine {
  kind: DiffLineKind;
  oldLine?: string;
  newLine?: string;
  oldNum?: number;
  newNum?: number;
}

export function computeLineDiff(oldText: string, newText: string): DiffLine[] {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const max = Math.max(oldLines.length, newLines.length);
  const result: DiffLine[] = [];

  for (let i = 0; i < max; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];

    if (oldLine === undefined && newLine !== undefined) {
      result.push({ kind: "add", newLine, newNum: i + 1 });
    } else if (newLine === undefined && oldLine !== undefined) {
      result.push({ kind: "remove", oldLine, oldNum: i + 1 });
    } else if (oldLine === newLine) {
      result.push({ kind: "same", oldLine, newLine, oldNum: i + 1, newNum: i + 1 });
    } else {
      result.push({
        kind: "change",
        oldLine,
        newLine,
        oldNum: i + 1,
        newNum: i + 1,
      });
    }
  }

  return result;
}