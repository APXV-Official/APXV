import { authHeaders, getApiConfig, notifyUnauthorized } from "./configure";
import { ApiError } from "./http";

export interface UploadFileInfo {
  filename: string;
  size: number;
  stored_path: string;
}

export interface UploadSession {
  upload_id: string;
  label?: string;
  files?: UploadFileInfo[];
  created_at?: string;
}

export async function createUpload(
  files: File[],
  label = "",
): Promise<UploadSession> {
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/$/, "");
  const form = new FormData();
  if (label) form.append("label", label);
  for (const file of files) {
    form.append("files", file, file.name);
  }

  const headers: Record<string, string> = authHeaders(config.apiKey);

  const response = await fetch(`${base}/api/v2/uploads`, {
    method: "POST",
    headers,
    body: form,
  });

  const text = await response.text();
  let payload: Record<string, unknown> = {};
  if (text) {
    try {
      payload = JSON.parse(text) as Record<string, unknown>;
    } catch {
      payload = { message: text };
    }
  }

  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(response.status, {
      error: String(payload.error ?? "upload_failed"),
      message: String(payload.message ?? text),
      details: payload.details as Record<string, unknown> | undefined,
    });
  }

  const session = payload.session as UploadSession | undefined;
  return session ?? (payload as unknown as UploadSession);
}