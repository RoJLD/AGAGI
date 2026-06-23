import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api/client";

export type WsStatus = "connecting" | "open" | "closed" | "error";

interface Options {
  enabled?: boolean;
  reconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
}

/**
 * WebSocket réutilisable : reconnexion à backoff exponentiel borné, statut, cleanup propre.
 * `onMessage` est stabilisé via ref → pas de reconnexion à chaque re-render.
 */
export function useWebSocket<T = unknown>(
  path: string,
  onMessage: (data: T) => void,
  options: Options = {},
): { status: WsStatus } {
  const { enabled = true, reconnectDelayMs = 1000, maxReconnectDelayMs = 30_000 } = options;
  const [status, setStatus] = useState<WsStatus>("connecting");
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let closedByUs = false;
    let openedAt = 0;

    const connect = () => {
      setStatus("connecting");
      ws = new WebSocket(wsUrl(path));

      ws.onopen = () => {
        openedAt = Date.now();
        attempts = 0;
        setStatus("open");
      };
      ws.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data) as T);
        } catch {
          console.warn(`useWebSocket(${path}) : message non-JSON ignoré`);
        }
      };
      ws.onerror = () => setStatus("error");
      ws.onclose = () => {
        setStatus("closed");
        if (closedByUs) return;
        // reset du backoff si la connexion avait tenu plus de 5 s
        if (openedAt && Date.now() - openedAt > 5000) attempts = 0;
        const delay = Math.min(reconnectDelayMs * 2 ** attempts, maxReconnectDelayMs);
        attempts += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [path, enabled, reconnectDelayMs, maxReconnectDelayMs]);

  return { status };
}
