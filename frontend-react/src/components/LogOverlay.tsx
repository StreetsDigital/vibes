import { useState, useEffect, useRef } from 'preact/hooks';

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  source: string;
}

interface LogOverlayProps {
  maxSizeMB?: number;
}

export function LogOverlay({ maxSizeMB = 500 }: LogOverlayProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [minimized, setMinimized] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [currentSize, setCurrentSize] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch logs periodically
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('/api/logs?limit=100&filter=' + filter);
        const data = await res.json();
        if (data.logs) {
          setLogs(prev => {
            // Merge new logs, dedupe by id
            const existing = new Set(prev.map(l => l.id));
            const newLogs = data.logs.filter((l: LogEntry) => !existing.has(l.id));
            const combined = [...prev, ...newLogs];

            // Calculate size and trim if needed
            const size = new Blob([JSON.stringify(combined)]).size;
            setCurrentSize(size);

            // If over limit, process and trim oldest 20%
            if (size > maxSizeMB * 1024 * 1024) {
              const trimCount = Math.floor(combined.length * 0.2);
              return combined.slice(trimCount);
            }

            return combined.slice(-1000); // Keep last 1000 entries max in UI
          });
        }
      } catch (e) {
        // Silently fail
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [filter, maxSizeMB]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (!minimized && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, minimized]);

  const filteredLogs = logs.filter(log => {
    if (search && !log.message.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error': return 'text-red-400';
      case 'warn': case 'warning': return 'text-yellow-400';
      case 'info': return 'text-blue-400';
      case 'debug': return 'text-gray-500';
      default: return 'text-gray-400';
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-4 right-4 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-400 hover:bg-gray-700 hover:text-white z-50 flex items-center gap-2 shadow-lg"
      >
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
        Logs ({filteredLogs.length})
      </button>
    );
  }

  return (
    <div
      ref={containerRef}
      className="fixed bottom-4 right-4 w-[500px] h-[300px] bg-gray-900 border border-gray-700 rounded-lg shadow-2xl z-50 flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700 bg-gray-800 rounded-t-lg">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs font-medium text-gray-300">Live Logs</span>
          <span className="text-xs text-gray-500">({formatSize(currentSize)} / {maxSizeMB}MB)</span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter((e.target as HTMLSelectElement).value)}
            className="bg-gray-700 text-xs rounded px-2 py-1 text-gray-300 border-none outline-none"
          >
            <option value="all">All</option>
            <option value="error">Errors</option>
            <option value="warn">Warnings</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
          <button
            onClick={() => setMinimized(true)}
            className="text-gray-400 hover:text-white p-1"
            title="Minimize"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-2 py-1 border-b border-gray-800">
        <input
          type="text"
          placeholder="Search logs..."
          value={search}
          onInput={(e) => setSearch((e.target as HTMLInputElement).value)}
          className="w-full bg-gray-800 text-xs rounded px-2 py-1 text-gray-300 placeholder-gray-500 outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-0.5">
        {filteredLogs.map((log) => (
          <div
            key={log.id}
            className="flex gap-2 hover:bg-gray-800 px-1 rounded cursor-default"
            title={log.message}
          >
            <span className="text-gray-600 flex-shrink-0">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <span className={`flex-shrink-0 w-12 ${getLevelColor(log.level)}`}>
              [{log.level.slice(0, 5).toUpperCase()}]
            </span>
            <span className="text-gray-300 truncate">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>

      {/* Footer */}
      <div className="px-3 py-1 border-t border-gray-700 text-xs text-gray-500 flex justify-between">
        <span>{filteredLogs.length} entries</span>
        <button
          onClick={() => setLogs([])}
          className="text-gray-500 hover:text-red-400"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
