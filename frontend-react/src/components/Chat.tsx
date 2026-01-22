import { useState, useRef, useEffect } from 'preact/hooks';
import type { ChatMessage, LogEntry } from '../types';
import { ActionSheet, Modal } from './Modal';
import { useMcpServers } from '../hooks/useApi';
import { Toggle } from './Toggle';

const VISIBLE_MESSAGE_COUNT = 6;

interface ChatProps {
  messages: ChatMessage[];
  loading: boolean;
  branch: string;
  onSend: (message: string) => void;
  onStop: () => void;
  onClear: () => void;
  onShowAddTask: () => void;
  isVisible?: boolean;
}

export function Chat({ messages, loading, branch, onSend, onStop, onClear, onShowAddTask, isVisible }: ChatProps) {
  const [input, setInput] = useState('');
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [showDebugLogs, setShowDebugLogs] = useState(false);
  const [showMcpPanel, setShowMcpPanel] = useState(false);
  const [showAllMessages, setShowAllMessages] = useState(false);
  const [debugLogs, setDebugLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Calculate visible messages (show last N)
  const hiddenCount = Math.max(0, messages.length - VISIBLE_MESSAGE_COUNT);
  const visibleMessages = hiddenCount > 0 ? messages.slice(-VISIBLE_MESSAGE_COUNT) : messages;
  const messagesRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollRef = useRef<number | null>(null);

  // MCP Servers
  const mcpApi = useMcpServers();
  const enabledMcpCount = mcpApi.servers.filter(s => s.enabled).length;

  // Load MCP servers on mount
  useEffect(() => {
    mcpApi.load();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, debugLogs]);

  // Scroll to bottom when tab becomes visible
  useEffect(() => {
    if (isVisible && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [isVisible]);

  // Load debug logs
  const loadDebugLogs = async () => {
    try {
      const response = await fetch('/api/logs?limit=100');
      const data = await response.json();
      setDebugLogs(data.logs || []);
    } catch (e) {
      console.error('Failed to load debug logs:', e);
    }
  };

  // Poll for logs when debug mode is on
  useEffect(() => {
    if (showDebugLogs) {
      setLogsLoading(true);
      loadDebugLogs().finally(() => setLogsLoading(false));
      pollRef.current = window.setInterval(loadDebugLogs, 3000);
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, [showDebugLogs]);

  // Auto-resize textarea (max 200px height for longer messages)
  const autoResize = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  };

  const handleSend = () => {
    const message = input.trim();
    if (!message || loading) return;
    onSend(message);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickPrompt = (text: string) => {
    onSend(text);
  };

  const formatMessage = (text: string) => {
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks
    escaped = escaped.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
      return `<pre class="bg-gray-900 rounded p-3 my-2 overflow-x-auto text-xs font-mono"><code>${code.trim()}</code></pre>`;
    });

    // Inline code
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="bg-gray-900 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>');

    // Bold and italic
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Line breaks
    escaped = escaped.replace(/\n/g, '<br>');

    return escaped;
  };

  const formatLogTime = (timestamp: string) => {
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

  const levelColors: Record<string, string> = {
    info: 'text-blue-400',
    warn: 'text-yellow-400',
    error: 'text-red-400',
    debug: 'text-gray-500',
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header - Sticky */}
      <div className="bg-gray-800 rounded-xl mx-3 mt-3 p-3 flex items-center justify-between flex-shrink-0 sticky top-0 z-10">
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <p className="text-sm text-gray-300 truncate">{branch}</p>
          {/* MCP Servers Toggle */}
          <button
            onClick={() => setShowMcpPanel(!showMcpPanel)}
            className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 transition-colors ${
              showMcpPanel
                ? 'bg-green-600/30 text-green-400 border border-green-500/50'
                : mcpApi.servers.length > 0
                ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600'
            }`}
            title={`${enabledMcpCount}/${mcpApi.servers.length} MCP servers enabled`}
          >
            <span className={`w-2 h-2 rounded-full ${enabledMcpCount > 0 ? 'bg-green-400' : 'bg-gray-500'}`} />
            MCPs {mcpApi.servers.length > 0 && <span className="text-gray-500">({enabledMcpCount}/{mcpApi.servers.length})</span>}
          </button>
          {/* Debug Logs Toggle */}
          <button
            onClick={() => setShowDebugLogs(!showDebugLogs)}
            className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 transition-colors ${
              showDebugLogs
                ? 'bg-purple-600/30 text-purple-400 border border-purple-500/50'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
            title={showDebugLogs ? 'Hide debug logs' : 'Show debug logs'}
          >
            <span className={`w-2 h-2 rounded-full ${showDebugLogs ? 'bg-purple-400 animate-pulse' : 'bg-gray-500'}`} />
            Debug
          </button>
        </div>
        <button
          onClick={() => quickPrompt('Create a PR for current changes')}
          className="ml-2 px-3 py-1 text-sm font-medium hover:bg-gray-700 rounded"
        >
          View PR
        </button>
        <button
          onClick={() => setShowActionMenu(true)}
          className="ml-1 p-1.5 hover:bg-gray-700 rounded"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>
      </div>

      {/* MCP Servers Panel */}
      {showMcpPanel && (
        <div className="mx-3 mt-2 bg-gray-800/80 backdrop-blur rounded-xl border border-green-500/30 overflow-hidden">
          <div className="p-3 border-b border-gray-700 flex items-center justify-between">
            <span className="text-sm font-medium text-green-400">MCP Servers</span>
            <button
              onClick={() => setShowMcpPanel(false)}
              className="text-gray-400 hover:text-white p-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-3 space-y-2 max-h-48 overflow-y-auto">
            {mcpApi.servers.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-2">
                No MCP servers configured
                <div className="text-xs mt-1">Add servers in the Tools tab</div>
              </div>
            ) : (
              mcpApi.servers.map(server => (
                <div
                  key={`${server.scope}-${server.name}`}
                  className="flex items-center justify-between p-2 bg-gray-900/50 rounded-lg"
                >
                  <div className="flex-1 min-w-0 mr-3">
                    <div className="text-sm font-medium truncate">{server.name}</div>
                    <div className="text-xs text-gray-500 truncate">
                      {server.scope} • {server.command} {server.args?.join(' ')}
                    </div>
                  </div>
                  <Toggle
                    checked={server.enabled}
                    onChange={(enabled) => mcpApi.toggle(server.name, server.scope, enabled)}
                  />
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Messages + Debug Logs */}
      <div ref={messagesRef} className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && !showDebugLogs ? (
          <div className="text-gray-500 text-sm text-center py-8">
            Start a conversation with Claude
          </div>
        ) : (
          <>
            {/* See earlier messages button */}
            {hiddenCount > 0 && (
              <button
                onClick={() => setShowAllMessages(true)}
                className="w-full py-2 px-4 text-sm text-gray-400 hover:text-white bg-gray-800/50 hover:bg-gray-800 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
                See {hiddenCount} earlier message{hiddenCount > 1 ? 's' : ''}
              </button>
            )}
            {visibleMessages.map((msg, i) => (
              <div
                key={`msg-${hiddenCount + i}`}
                className={
                  msg.role === 'user'
                    ? 'bg-blue-600 rounded-lg p-3 ml-4 md:ml-8'
                    : msg.role === 'error'
                    ? 'bg-red-600/20 text-red-400 rounded-lg p-3'
                    : 'bg-gray-700 rounded-lg p-3 mr-4 md:mr-8'
                }
              >
                <div
                  className="text-sm chat-content"
                  dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
                />
              </div>
            ))}
          </>
        )}

        {/* Debug Logs Section */}
        {showDebugLogs && (
          <div className="border-t border-purple-500/30 pt-3 mt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-purple-400 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                Claude Debug Logs
                {logsLoading && <span className="text-gray-500 ml-1">(loading...)</span>}
              </span>
              <span className="text-xs text-gray-500">{debugLogs.length} entries</span>
            </div>
            <div className="space-y-1 font-mono text-xs bg-gray-950 rounded-lg p-2 max-h-64 overflow-y-auto">
              {debugLogs.length === 0 ? (
                <div className="text-gray-500 text-center py-4">No debug logs yet</div>
              ) : (
                debugLogs.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-start gap-2 py-0.5 hover:bg-gray-800/50 rounded px-1"
                  >
                    <span className="text-gray-600 flex-shrink-0">
                      {formatLogTime(log.timestamp)}
                    </span>
                    <span className={`flex-shrink-0 ${levelColors[log.level] || 'text-gray-400'}`}>
                      [{log.level.toUpperCase().slice(0, 4)}]
                    </span>
                    <span className="text-gray-300 break-all">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {loading && (
          <div className="bg-gray-700 rounded-lg p-3 mr-4 md:mr-8">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></span>
            </div>
          </div>
        )}
      </div>

      {/* Input - Sticky Bottom */}
      <div className="p-3 flex-shrink-0 safe-bottom sticky bottom-0 bg-gray-900 z-10">
        <div className="bg-gray-800 rounded-xl p-3">
          <textarea
            ref={textareaRef}
            value={input}
            onInput={(e) => {
              setInput((e.target as HTMLTextAreaElement).value);
              autoResize();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Add feedback..."
            rows={1}
            className="w-full bg-transparent text-base focus:outline-none resize-none overflow-y-auto"
            style={{ minHeight: '24px', maxHeight: '200px' }}
          />

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700">
            <div className="flex items-center gap-1">
              <span className="text-xs bg-gray-700 px-2 py-1 rounded-full text-gray-400">
                StreetsDigital/vibes
              </span>
            </div>
            <div className="flex items-center gap-1">
              {/* Add task */}
              <button
                onClick={onShowAddTask}
                className="p-2 hover:bg-gray-700 rounded-lg active:bg-gray-600"
                title="Add task"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
              {/* Commit */}
              <button
                onClick={() => quickPrompt('/commit')}
                className="p-2 hover:bg-gray-700 rounded-lg active:bg-gray-600"
                title="Commit"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
              {/* PR */}
              <button
                onClick={() => quickPrompt('Create a pull request')}
                className="p-2 hover:bg-gray-700 rounded-lg active:bg-gray-600"
                title="Create PR"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </button>
              {/* Send / Stop */}
              {loading ? (
                <button
                  onClick={onStop}
                  className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 active:bg-red-700 ml-1"
                  title="Stop"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
                  </svg>
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  className="p-2 bg-white text-gray-900 rounded-lg hover:bg-gray-200 active:bg-gray-300 ml-1"
                  title="Send"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Menu */}
      <ActionSheet isOpen={showActionMenu} onClose={() => setShowActionMenu(false)}>
        <div className="space-y-1">
          <button
            onClick={() => { quickPrompt('Summarize current tasks'); setShowActionMenu(false); }}
            className="w-full text-left px-4 py-3 hover:bg-gray-700 rounded-lg"
          >
            Summarize tasks
          </button>
          <button
            onClick={() => { quickPrompt('What should I work on next?'); setShowActionMenu(false); }}
            className="w-full text-left px-4 py-3 hover:bg-gray-700 rounded-lg"
          >
            Suggest next task
          </button>
          <button
            onClick={() => { quickPrompt('/verify'); setShowActionMenu(false); }}
            className="w-full text-left px-4 py-3 hover:bg-gray-700 rounded-lg"
          >
            Run quality checks
          </button>
          <button
            onClick={() => { quickPrompt('Show git status'); setShowActionMenu(false); }}
            className="w-full text-left px-4 py-3 hover:bg-gray-700 rounded-lg"
          >
            Git status
          </button>
          <button
            onClick={() => { onClear(); setShowActionMenu(false); }}
            className="w-full text-left px-4 py-3 hover:bg-gray-700 rounded-lg text-red-400"
          >
            Clear chat history
          </button>
          <button
            onClick={() => setShowActionMenu(false)}
            className="w-full text-left px-4 py-3 text-gray-400 hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
        </div>
      </ActionSheet>

      {/* All Messages Modal */}
      <Modal isOpen={showAllMessages} onClose={() => setShowAllMessages(false)} title="Chat History">
        <div className="space-y-3 max-h-[70vh] overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={`modal-msg-${i}`}
              className={
                msg.role === 'user'
                  ? 'bg-blue-600 rounded-lg p-3 ml-4'
                  : msg.role === 'error'
                  ? 'bg-red-600/20 text-red-400 rounded-lg p-3'
                  : 'bg-gray-700 rounded-lg p-3 mr-4'
              }
            >
              <div
                className="text-sm chat-content"
                dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
              />
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
