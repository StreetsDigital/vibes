import { useEffect, useRef } from 'preact/hooks';
import { useLogs } from '../hooks/useApi';
import type { LogFilter } from '../hooks/useApi';
import type { LogEntry } from '../types';

export function LogsPanel() {
  const {
    logs,
    filter,
    loading,
    autoScroll,
    polling,
    load,
    clear,
    changeFilter,
    setAutoScroll,
    startPolling,
    stopPolling,
  } = useLogs();

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Load logs on mount and start polling
  useEffect(() => {
    load();
    startPolling();
    return () => stopPolling();
  }, []);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const levelColors: Record<string, string> = {
    info: 'text-blue-400',
    warn: 'text-yellow-400',
    error: 'text-red-400',
    debug: 'text-gray-500',
  };

  const sourceColors: Record<string, string> = {
    claude: 'bg-purple-600/20 text-purple-400',
    system: 'bg-gray-600/20 text-gray-400',
    container: 'bg-blue-600/20 text-blue-400',
    api: 'bg-green-600/20 text-green-400',
  };

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="font-semibold text-gray-300">Logs</h2>
            <p className="text-xs text-gray-500">Activity and system logs</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Filter dropdown */}
            <select
              value={filter}
              onChange={(e) => changeFilter((e.target as HTMLSelectElement).value as LogFilter)}
              className="text-xs bg-gray-700 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="claude">Claude</option>
              <option value="system">System</option>
              <option value="error">Errors</option>
            </select>

            {/* Refresh button */}
            <button
              onClick={() => load()}
              disabled={loading}
              className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
              title="Refresh"
            >
              <span className={loading ? 'animate-spin inline-block' : ''}>↻</span>
            </button>

            {/* Clear button */}
            <button
              onClick={clear}
              className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 text-red-400"
              title="Clear logs"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Polling indicator */}
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={polling ? stopPolling : startPolling}
            className={`flex items-center gap-1 px-2 py-1 rounded ${
              polling
                ? 'bg-green-600/20 text-green-400'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${polling ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
            {polling ? 'Live' : 'Paused'}
          </button>
          <span className="text-gray-500">{logs.length} entries</span>
        </div>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs bg-gray-950">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            {loading ? 'Loading logs...' : 'No logs yet'}
          </div>
        ) : (
          logs.map((log) => (
            <LogLine key={log.id} log={log} levelColors={levelColors} sourceColors={sourceColors} formatTime={formatTime} />
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      {/* Footer with auto-scroll toggle */}
      <div className="p-2 border-t border-gray-700 flex items-center justify-between flex-shrink-0">
        <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll((e.target as HTMLInputElement).checked)}
            className="rounded bg-gray-700 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          Auto-scroll
        </label>
        <span className="text-xs text-gray-500">
          {logs.length > 0 && `Last: ${formatTime(logs[logs.length - 1].timestamp)}`}
        </span>
      </div>
    </div>
  );
}

// Individual log line component
function LogLine({
  log,
  levelColors,
  sourceColors,
  formatTime,
}: {
  log: LogEntry;
  levelColors: Record<string, string>;
  sourceColors: Record<string, string>;
  formatTime: (ts: string) => string;
}) {
  return (
    <div className="flex items-start gap-2 py-1 px-2 hover:bg-gray-800/50 rounded group">
      {/* Timestamp */}
      <span className="text-gray-600 flex-shrink-0 w-16">
        {formatTime(log.timestamp)}
      </span>

      {/* Level indicator */}
      <span className={`flex-shrink-0 w-12 ${levelColors[log.level] || 'text-gray-400'}`}>
        [{log.level.toUpperCase().slice(0, 4)}]
      </span>

      {/* Source badge */}
      <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] ${sourceColors[log.source] || 'bg-gray-600/20 text-gray-400'}`}>
        {log.source}
      </span>

      {/* Message */}
      <span className="text-gray-300 break-all flex-1">
        {log.message}
      </span>

      {/* Metadata indicator */}
      {log.metadata && Object.keys(log.metadata).length > 0 && (
        <span className="text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity" title={JSON.stringify(log.metadata, null, 2)}>
          {'{ }'}
        </span>
      )}
    </div>
  );
}
