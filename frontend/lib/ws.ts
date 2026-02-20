const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const deriveWsFromApiBase = () => {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase || apiBase.startsWith("/")) {
    return null;
  }

  try {
    const apiUrl = new URL(apiBase);
    const protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${apiUrl.host}`;
  } catch {
    return null;
  }
};

const getDefaultWsOrigin = () => {
  const fromApiBase = deriveWsFromApiBase();
  if (fromApiBase) {
    return fromApiBase;
  }
  return "ws://localhost:8000";
};

export const buildDebateWsUrl = (debateId: string, token?: string) => {
  const wsOrigin = trimTrailingSlash(
    process.env.NEXT_PUBLIC_WS_URL || getDefaultWsOrigin(),
  );
  const url = new URL(`${wsOrigin}/api/v1/ws/debates/${debateId}`);

  if (token) {
    url.searchParams.set("token", token);
  }

  return url.toString();
};
