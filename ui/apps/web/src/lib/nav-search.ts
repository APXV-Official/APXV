/** Default search params when resetting typed TanStack routes via sidebar nav. */
export function defaultNavSearch(
  to: string,
): Record<string, unknown> | undefined {
  switch (to) {
    case "/workshop":
      return { id: undefined, shelf: undefined };
    case "/studio":
      return { tab: undefined };
    case "/packs":
      return { wizard: undefined, pack: undefined };
    case "/workshop/composer":
    case "/workshop/canvas":
      return { id: undefined };
    case "/jobs":
      return { id: undefined };
    case "/verify":
      return { hash: undefined, job: undefined };
    case "/governance":
      return { tab: undefined, proposal: undefined };
    case "/system":
      return { tab: undefined };
    case "/trust":
      return undefined;
    default:
      return undefined;
  }
}
