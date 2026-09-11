const LOCAL_API_URL = "http://127.0.0.1:8000";
const RENDER_API_URL = "https://smarte-muelltonne-2-api.onrender.com";

function isRenderHost() {
  return typeof window !== "undefined" && window.location.hostname.endsWith(".onrender.com");
}

function getNetworkLocalApiUrl() {
  if (typeof window === "undefined") return LOCAL_API_URL;

  const { hostname, protocol } = window.location;
  const isLoopback = hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";

  if (isLoopback) return LOCAL_API_URL;
  return `${protocol}//${hostname}:8000`;
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || (isRenderHost() ? RENDER_API_URL : getNetworkLocalApiUrl());
}

export function getWebSocketUrl() {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const apiUrl = getApiBaseUrl();
  const wsProtocol = apiUrl.startsWith("https://") ? "wss://" : "ws://";
  return `${apiUrl.replace(/^https?:\/\//, wsProtocol)}/ws/live`;
}
