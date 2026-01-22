/**
 * Real-time hooks for WebSocket and SSE connections
 *
 * Provides instant updates instead of polling:
 * - useWebSocket: Full duplex for board, chat, task updates
 * - useSSE: Streaming for Claude output, logs
 * - useTaskProgress: Live task stage tracking
 */

import { useState, useEffect, useCallback, useRef } from 'preact/hooks';

// Types
export interface TaskProgress {
  task_id: string;
  task_name: string;
  stage: string;
  stage_emoji: string;
  stage_display: string;
  stage_message: string;
  started_at: string;
  updated_at: string;
  progress_percent: number;
  retro?: string;
  error?: string;
}

export interface RealtimeStatus {
  websocket_enabled: boolean;
  sse_enabled: boolean;
  endpoints: {
    websocket: string | null;
    sse_events: string;
    sse_chat: string;
    sse_logs: string;
  };
}

// Get API base for current context
function getApiBase(): string {
  const path = window.location.pathname;
  const projectMatch = path.match(/^\/project\/([^/]+)/);
  if (projectMatch) {
    return `/project/${projectMatch[1]}`;
  }
  return '';
}

const API_BASE = getApiBase();

/**
 * WebSocket hook for real-time bi-directional communication
 */
export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<any>(null);
  const listenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map());

  useEffect(() => {
    // Dynamic import for socket.io-client
    const connectSocket = async () => {
      try {
        // Check if WebSocket is available
        const statusRes = await fetch(`${API_BASE}/api/realtime/status`);
        const status: RealtimeStatus = await statusRes.json();

        if (!status.websocket_enabled) {
          console.log('[WS] WebSocket not enabled, using SSE fallback');
          return;
        }

        // Import socket.io dynamically
        const { io } = await import('socket.io-client');

        const wsUrl = window.location.origin;
        socketRef.current = io(wsUrl, {
          path: `${API_BASE}/socket.io`,
          transports: ['websocket', 'polling']
        });

        socketRef.current.on('connect', () => {
          console.log('[WS] Connected');
          setConnected(true);
          setError(null);
        });

        socketRef.current.on('disconnect', () => {
          console.log('[WS] Disconnected');
          setConnected(false);
        });

        socketRef.current.on('connect_error', (err: Error) => {
          console.error('[WS] Connection error:', err);
          setError(err.message);
        });

        // Forward all events to listeners
        socketRef.current.onAny((event: string, data: any) => {
          const listeners = listenersRef.current.get(event);
          if (listeners) {
            listeners.forEach(callback => callback(data));
          }
        });

      } catch (err) {
        console.log('[WS] WebSocket not available, will use SSE');
      }
    };

    connectSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const subscribe = useCallback((event: string, callback: (data: any) => void) => {
    if (!listenersRef.current.has(event)) {
      listenersRef.current.set(event, new Set());
    }
    listenersRef.current.get(event)!.add(callback);

    return () => {
      listenersRef.current.get(event)?.delete(callback);
    };
  }, []);

  const emit = useCallback((event: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  return { connected, error, subscribe, emit };
}

/**
 * SSE hook for server-sent events streaming
 */
export function useSSE(endpoint: string, autoConnect = true) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const listenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map());

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${API_BASE}${endpoint}`;
    eventSourceRef.current = new EventSource(url);

    eventSourceRef.current.onopen = () => {
      console.log(`[SSE] Connected to ${endpoint}`);
      setConnected(true);
      setError(null);
    };

    eventSourceRef.current.onerror = (e) => {
      console.error(`[SSE] Error on ${endpoint}:`, e);
      setError('Connection lost');
      setConnected(false);
    };

    // Listen for all event types
    const eventTypes = [
      'connected', 'board:update', 'chat:message', 'chat:stream',
      'chat:stream:end', 'task:progress', 'logs', 'chunk', 'done', 'error'
    ];

    eventTypes.forEach(eventType => {
      eventSourceRef.current!.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          const listeners = listenersRef.current.get(eventType);
          if (listeners) {
            listeners.forEach(callback => callback(data));
          }
        } catch (err) {
          console.error(`[SSE] Parse error for ${eventType}:`, err);
        }
      });
    });
  }, [endpoint]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  const subscribe = useCallback((event: string, callback: (data: any) => void) => {
    if (!listenersRef.current.has(event)) {
      listenersRef.current.set(event, new Set());
    }
    listenersRef.current.get(event)!.add(callback);

    return () => {
      listenersRef.current.get(event)?.delete(callback);
    };
  }, []);

  return { connected, error, connect, disconnect, subscribe };
}

/**
 * Hook for streaming chat responses
 */
export function useStreamingChat() {
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (
    message: string,
    onChunk?: (chunk: string) => void,
    onComplete?: (fullContent: string) => void
  ) => {
    setStreaming(true);
    setStreamContent('');
    setError(null);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE}/api/stream/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: abortControllerRef.current.signal
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            // Skip event type line, data follows
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.text) {
                fullContent += data.text;
                setStreamContent(fullContent);
                onChunk?.(data.text);
              } else if (data.content) {
                // Done event
                onComplete?.(data.content);
              } else if (data.error) {
                setError(data.error);
              }
            } catch {
              // Ignore parse errors for incomplete data
            }
          }
        }
      }

    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message);
      }
    } finally {
      setStreaming(false);
      abortControllerRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreaming(false);
  }, []);

  return { streaming, streamContent, error, sendMessage, stop };
}

/**
 * Hook for live task progress tracking
 */
export function useTaskProgress() {
  const [tasks, setTasks] = useState<TaskProgress[]>([]);
  const { subscribe } = useSSE('/api/stream/events');

  useEffect(() => {
    const unsubscribe = subscribe('task:progress', (data: TaskProgress) => {
      setTasks(prev => {
        const existing = prev.findIndex(t => t.task_id === data.task_id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = data;
          return updated;
        }
        return [...prev, data];
      });

      // Auto-remove completed/failed tasks after delay
      if (data.stage === 'completed' || data.stage === 'failed') {
        setTimeout(() => {
          setTasks(prev => prev.filter(t => t.task_id !== data.task_id));
        }, 30000);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  return { tasks };
}

/**
 * Hook for real-time board updates
 */
export function useLiveBoard() {
  const [board, setBoard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const ws = useWebSocket();
  const sse = useSSE('/api/stream/events', !ws.connected);

  // Initial load
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/board`);
        const data = await res.json();
        setBoard(data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Subscribe to updates
  useEffect(() => {
    const handleUpdate = (data: any) => {
      setBoard(data);
    };

    // Try WebSocket first, fall back to SSE
    if (ws.connected) {
      return ws.subscribe('board:update', handleUpdate);
    } else {
      return sse.subscribe('board:update', handleUpdate);
    }
  }, [ws.connected, ws.subscribe, sse.subscribe]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/board`);
      const data = await res.json();
      setBoard(data);
    } finally {
      setLoading(false);
    }
  }, []);

  return { board, loading, refresh };
}

/**
 * Hook for real-time logs streaming
 */
export function useLiveLogs(filter: string = 'all') {
  const [logs, setLogs] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${API_BASE}/api/stream/logs?filter=${filter}`;
    eventSourceRef.current = new EventSource(url);

    eventSourceRef.current.onopen = () => setConnected(true);
    eventSourceRef.current.onerror = () => setConnected(false);

    eventSourceRef.current.addEventListener('logs', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data.entries) {
          setLogs(prev => [...prev, ...data.entries].slice(-200));
        }
      } catch {}
    });

    eventSourceRef.current.addEventListener('connected', () => {
      setLogs([]);  // Clear on reconnect
    });
  }, [filter]);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  const clear = useCallback(() => setLogs([]), []);

  return { logs, connected, connect, disconnect, clear };
}
