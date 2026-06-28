type TokenSearchParams = {
  get(name: string): string | null;
};

const TOKEN_QUERY_KEY = "token";

const readTokenFromHash = (hash: string): string => {
  const rawHash = hash.startsWith("#") ? hash.slice(1) : hash;
  const paramHash = rawHash.startsWith("?") ? rawHash.slice(1) : rawHash;
  if (!paramHash) {
    return "";
  }
  return new URLSearchParams(paramHash).get(TOKEN_QUERY_KEY)?.trim() ?? "";
};

export const readOneTimeTokenFromUrl = (
  searchParams?: TokenSearchParams | null
): string => {
  const queryToken = searchParams?.get(TOKEN_QUERY_KEY)?.trim();
  if (queryToken) {
    return queryToken;
  }
  if (typeof window === "undefined") {
    return "";
  }
  return readTokenFromHash(window.location.hash);
};

export const clearOneTimeTokenFromUrl = () => {
  if (typeof window === "undefined") {
    return;
  }

  const url = new URL(window.location.href);
  let changed = false;

  if (url.searchParams.has(TOKEN_QUERY_KEY)) {
    url.searchParams.delete(TOKEN_QUERY_KEY);
    changed = true;
  }

  const rawHash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
  const paramHash = rawHash.startsWith("?") ? rawHash.slice(1) : rawHash;
  if (paramHash) {
    const hashParams = new URLSearchParams(paramHash);
    if (hashParams.has(TOKEN_QUERY_KEY)) {
      hashParams.delete(TOKEN_QUERY_KEY);
      const nextHash = hashParams.toString();
      url.hash = nextHash ? `#${nextHash}` : "";
      changed = true;
    }
  }

  if (!changed) {
    return;
  }

  const query = url.searchParams.toString();
  window.history.replaceState(
    window.history.state,
    "",
    `${url.pathname}${query ? `?${query}` : ""}${url.hash}`
  );
};
