function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadJson(filename: string, data: unknown): void {
  downloadBlob(
    filename,
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
}

export function downloadText(filename: string, text: string, mime = "text/markdown"): void {
  downloadBlob(filename, new Blob([text], { type: `${mime};charset=utf-8` }));
}