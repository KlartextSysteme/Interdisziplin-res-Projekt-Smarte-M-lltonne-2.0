"use client";

import { useEffect, useRef, useState } from "react";
import type { LiveData } from "@/types";
import { getWebSocketUrl } from "@/lib/runtimeConfig";

export function useLiveData(): LiveData | null {
  const [data, setData] = useState<LiveData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let isMounted = true;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (!isMounted) return;
      const WS_URL = getWebSocketUrl();
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          setData(JSON.parse(event.data) as LiveData);
        } catch {
          // malformed frame — ignore
        }
      };

      ws.onclose = () => {
        if (isMounted) reconnectTimer = setTimeout(connect, 3_000); // reconnect after 3 s
      };

      ws.onerror = () => {
        try {
          ws.close(); // triggers onclose -> scheduled reconnect
        } catch {
          // ignore
        }
      };
    }

    connect();
    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  return data;
}
