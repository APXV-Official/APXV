/** Default search params when resetting typed TanStack routes via sidebar nav. */
export function defaultNavSearch(
  to: string,
): Record<string, unknown> | undefined {
  switch (to) {
    case "/packs":
      return { wizard: undefined, pack: undefined };
    case "/jobs":
      return { id: undefined };
    case "/verify":
      return { hash: undefined, job: undefined };
    case "/governance":
      return { tab: undefined, proposal: undefined };
    case "/system":
      return { tab: undefined };
    default:
      return undefined;
  }
}