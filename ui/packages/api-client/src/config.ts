import { createClient, createConfig } from "@hey-api/client-fetch";

export function createApxvClient(baseUrl = "") {
  const client = createClient(
    createConfig({
      baseUrl: baseUrl || undefined,
    }),
  );

  return client;
}

export type ApxvClient = ReturnType<typeof createApxvClient>;