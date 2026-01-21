import { useState } from 'preact/hooks';

interface ConfigRoute {
  file_path: string;
  section?: string;
  description: string;
  suggested_change?: string;
}

interface ConfigHelperProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ConfigHelper({ isOpen, onClose }: ConfigHelperProps) {
  const [query, setQuery] = useState('');
  const [route, setRoute] = useState<ConfigRoute | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setRoute(null);

    try {
      const response = await fetch('/api/config/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!response.ok) {
        throw new Error('Failed to route configuration request');
      }

      const data = await response.json();
      setRoute(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const openFileInEditor = (filePath: string) => {
    // This would typically open the file in the configured editor
    // For now, we'll just copy the path to clipboard
    navigator.clipboard.writeText(filePath);
    alert(`File path copied to clipboard: ${filePath}`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">Configuration Helper</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-300"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-400 mb-3">
              Describe what you want to configure, and I'll route you to the right file.
            </p>
            <form onSubmit={handleSubmit}>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={query}
                  onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
                  placeholder="e.g., change quality gate settings, add MCP server, configure git hooks..."
                  className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Routing...' : 'Find Config'}
                </button>
              </div>
            </form>
          </div>

          {error && (
            <div className="p-3 bg-red-900/20 border border-red-600/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {route && (
            <div className="space-y-3">
              <div className="p-4 bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-200">Configuration File</h3>
                  <button
                    onClick={() => openFileInEditor(route.file_path)}
                    className="text-xs px-2 py-1 bg-blue-600/20 text-blue-400 rounded hover:bg-blue-600/30"
                  >
                    Open File
                  </button>
                </div>
                <div className="space-y-2">
                  <div>
                    <span className="text-xs text-gray-500">File Path:</span>
                    <div className="text-sm font-mono text-gray-300 bg-gray-700/50 px-2 py-1 rounded">
                      {route.file_path}
                    </div>
                  </div>

                  {route.section && (
                    <div>
                      <span className="text-xs text-gray-500">Section:</span>
                      <div className="text-sm text-gray-300">{route.section}</div>
                    </div>
                  )}

                  <div>
                    <span className="text-xs text-gray-500">Description:</span>
                    <div className="text-sm text-gray-300">{route.description}</div>
                  </div>

                  {route.suggested_change && (
                    <div>
                      <span className="text-xs text-gray-500">Suggested Change:</span>
                      <div className="text-sm text-gray-300 bg-gray-700/50 px-2 py-1 rounded">
                        {route.suggested_change}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="text-xs text-gray-500">
                💡 Tip: The file path has been provided above. You can edit the file directly or use Claude to make the changes.
              </div>
            </div>
          )}

          <div className="pt-2">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Common Configurations:</h4>
            <div className="grid grid-cols-2 gap-2">
              {[
                "quality gates settings",
                "MCP server configuration",
                "git hooks setup",
                "Claude settings",
                "Docker configuration",
                "build scripts"
              ].map(example => (
                <button
                  key={example}
                  onClick={() => setQuery(example)}
                  className="text-left px-2 py-1 text-xs bg-gray-800 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-300"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}