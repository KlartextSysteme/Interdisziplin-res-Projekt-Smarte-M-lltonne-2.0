const LOCAL_API_URL = "http://localhost:8000";
const RENDER_API_URL = "https://smarte-muelltonne-2-api.onrender.com";

function isRenderHost() {
  return typeof window !== "undefined" && window.location.hostname.endsWith(".onrender.com");
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || (isRenderHost() ? RENDER_API_URL : LOCAL_API_URL);
}

export function getWebSocketUrl() {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const apiUrl = getApiBaseUrl();
  const wsProtocol = apiUrl.startsWith("https://") ? "wss://" : "ws://";
  return `${apiUrl.replace(/^https?:\/\//, wsProtocol)}/ws/live`;
}
