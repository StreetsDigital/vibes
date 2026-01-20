import { useState, useRef, useEffect } from 'preact/hooks';
import type { ChatMessage } from '../types';
import { ActionSheet } from './Modal';

interface ChatProps {
  messages: ChatMessage[];
  loading: boolean;
  branch: string;
  onSend: (message: string) => void;
  onStop: () => void;
  onClear: () => void;
  onShowAddTask: () => void;
}

export function Chat({ messages, loading, branch, onSend, onStop, onClear, onShowAddTask }: ChatProps) {
  const [input, setInput] = useState('');
  const [showActionMenu, setShowActionMenu] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-resize textarea
  const autoResize = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
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

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="bg-gray-800 rounded-xl mx-3 mt-3 p-3 flex items-center justify-between flex-shrink-0">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-300 truncate">{branch}</p>
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

      {/* Messages */}
      <div ref={messagesRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-gray-500 text-sm text-center py-8">
            Start a conversation with Claude
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
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
          ))
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

      {/* Input */}
      <div className="p-3 flex-shrink-0 safe-bottom">
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
            className="w-full bg-transparent text-base focus:outline-none resize-none overflow-hidden"
            style={{ minHeight: '24px', maxHeight: '120px' }}
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
    </div>
  );
}
