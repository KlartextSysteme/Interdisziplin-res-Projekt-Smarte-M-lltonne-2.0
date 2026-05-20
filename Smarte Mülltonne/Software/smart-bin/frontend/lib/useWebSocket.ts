"use client";

import { useEffect, useRef, useState } from "react";
import type { LiveData } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/live";

export function useLiveData(): LiveData | null {
  const [data, setData] = useState<LiveData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let isMounted = true;

    function connect() {
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
        if (isMounted) setTimeout(connect, 3_000); // reconnect after 3 s
      };
    }

    connect();
    return () => {
      isMounted = false;
      wsRef.current?.close();
    };
  }, []);

  return data;
}
