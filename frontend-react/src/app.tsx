import { useState, useEffect } from 'preact/hooks';
import type { ViewType, Task } from './types';
import { useBoard, useChat, useProjects, useGit, useSession } from './hooks/useApi';
import { Board } from './components/Board';
import { Chat } from './components/Chat';
import { ToolsPanel } from './components/ToolsPanel';

export function App() {
  const [currentView, setCurrentView] = useState<ViewType>('board');

  const board = useBoard();
  const chat = useChat();
  const projects = useProjects();
  const git = useGit();
  const session = useSession();

  // Initialize on mount
  useEffect(() => {
    board.refresh();
    chat.loadHistory();
    projects.load();
    git.loadBranch();
    checkSession();

    // Refresh board every 10 seconds
    const interval = setInterval(board.refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  // Check session for welcome-back message
  const checkSession = async () => {
    const data = await session.ping();
    if (data.summary) {
      setCurrentView('chat');
    }
  };

  // Handle task work request
  const handleWorkOnTask = (task: Task) => {
    setCurrentView('chat');
    chat.sendMessage(
      `Help me implement: ${task.name}\n\nDescription: ${task.description || 'None'}\n\nTest cases:\n${task.test_cases?.join('\n') || 'None'}`
    );
  };

  return (
    <div className="bg-gray-900 text-gray-100 min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-blue-400">⚡</h1>
            {/* Project Dropdown */}
            <ProjectDropdown
              projects={projects.projects}
              currentProject={projects.currentProject}
              onSwitch={async (path) => {
                await projects.switchProject(path);
                board.refresh();
                chat.loadHistory();
                git.loadBranch();
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 hidden sm:inline">
              {board.board?.stats
                ? `${board.board.stats.passing}/${board.board.stats.total} complete (${board.board.stats.progress_percent}%)`
                : 'Loading...'}
            </span>
            <button
              onClick={board.refresh}
              className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 active:bg-gray-500 text-sm"
            >
              ↻
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <div className="md:hidden flex border-b border-gray-700 bg-gray-800 flex-shrink-0">
        <TabButton
          active={currentView === 'board'}
          onClick={() => setCurrentView('board')}
          label="Board"
        />
        <TabButton
          active={currentView === 'chat'}
          onClick={() => setCurrentView('chat')}
          label="Claude"
        />
        <TabButton
          active={currentView === 'tools'}
          onClick={() => setCurrentView('tools')}
          label="Tools"
        />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Board View */}
        <main
          className={`flex-1 flex flex-col overflow-hidden ${
            currentView !== 'board' ? 'hidden md:flex' : 'flex'
          }`}
        >
          <Board
            data={board.board}
            onMoveTask={board.moveTask}
            onAddTask={board.createTask}
            onWorkOnTask={handleWorkOnTask}
          />
        </main>

        {/* Chat Sidebar */}
        <aside
          className={`w-full md:w-96 bg-gray-900 md:bg-gray-800 md:border-l border-gray-700 flex-col h-full ${
            currentView !== 'chat' ? 'hidden md:flex' : 'flex'
          }`}
        >
          <Chat
            messages={chat.messages}
            loading={chat.loading}
            branch={git.branch}
            onSend={chat.sendMessage}
            onClear={chat.clearHistory}
            onShowAddTask={() => setCurrentView('board')}
          />
        </aside>

        {/* Tools Panel */}
        <aside
          className={`w-full md:w-96 bg-gray-900 md:bg-gray-800 md:border-l border-gray-700 flex-col h-full ${
            currentView !== 'tools' ? 'hidden' : 'flex'
          }`}
        >
          <ToolsPanel />
        </aside>
      </div>
    </div>
  );
}

// Project Dropdown Component
function ProjectDropdown({
  projects,
  currentProject,
  onSwitch,
}: {
  projects: { name: string; path: string; current: boolean }[];
  currentProject: string;
  onSwitch: (path: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 px-2 py-1 bg-gray-700 rounded-lg hover:bg-gray-600 text-sm"
      >
        <span>{currentProject || 'vibes'}</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="absolute left-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
          <div className="py-1 max-h-60 overflow-y-auto">
            {projects.map((project) => (
              <button
                key={project.path}
                onClick={() => {
                  onSwitch(project.path);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-3 py-2 hover:bg-gray-700 text-sm ${
                  project.current ? 'text-blue-400' : ''
                }`}
              >
                {project.current && <span className="mr-1">●</span>}
                {project.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Tab Button Component
function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-3 text-sm font-medium text-center ${
        active ? 'tab-active text-blue-400' : 'text-gray-400'
      }`}
    >
      {label}
    </button>
  );
}
