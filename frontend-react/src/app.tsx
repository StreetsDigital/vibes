import { useState, useEffect } from 'preact/hooks';
import type { ViewType, Task } from './types';
import { useBoard, useChat, useProjects, useGit, useSession, useProjectManager } from './hooks/useApi';
import { Board } from './components/Board';
import { Chat } from './components/Chat';
import { ToolsPanel } from './components/ToolsPanel';
import { Modal } from './components/Modal';

export function App() {
  const [currentView, setCurrentView] = useState<ViewType>('board');
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);

  const board = useBoard();
  const chat = useChat();
  const projects = useProjects();
  const git = useGit();
  const session = useSession();
  const projectManager = useProjectManager();

  // Initialize on mount
  useEffect(() => {
    board.refresh();
    chat.loadHistory();
    projects.load();
    git.loadBranch();
    projectManager.loadProjects();
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
              managedProjects={projectManager.managedProjects}
              onSwitch={async (path) => {
                await projects.switchProject(path);
                board.refresh();
                chat.loadHistory();
                git.loadBranch();
              }}
              onOpenManaged={projectManager.openProject}
              onNewProject={() => setShowNewProjectModal(true)}
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

      {/* Desktop Tab Bar */}
      <div className="hidden md:flex border-b border-gray-700 bg-gray-800 flex-shrink-0 justify-center">
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
            currentView !== 'board' ? 'hidden' : 'flex'
          }`}
        >
          <Board
            data={board.board}
            onMoveTask={board.moveTask}
            onAddTask={board.createTask}
            onWorkOnTask={handleWorkOnTask}
          />
        </main>

        {/* Chat View */}
        <aside
          className={`w-full flex-1 bg-gray-900 flex-col h-full ${
            currentView !== 'chat' ? 'hidden' : 'flex'
          }`}
        >
          <Chat
            messages={chat.messages}
            loading={chat.loading}
            branch={git.branch}
            onSend={chat.sendMessage}
            onStop={chat.stopGeneration}
            onClear={chat.clearHistory}
            onShowAddTask={() => setCurrentView('board')}
          />
        </aside>

        {/* Tools Panel */}
        <aside
          className={`w-full flex-1 bg-gray-900 flex-col h-full overflow-y-auto ${
            currentView !== 'tools' ? 'hidden' : 'flex'
          }`}
        >
          <ToolsPanel />
        </aside>
      </div>

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onCreate={async (name, gitUrl) => {
          const result = await projectManager.createProject(name, gitUrl);
          if (result.success && result.project) {
            // Optionally open the new project
            projectManager.openProject(result.project.id);
          }
        }}
      />
    </div>
  );
}

// Project Dropdown Component
function ProjectDropdown({
  projects,
  currentProject,
  managedProjects,
  onSwitch,
  onOpenManaged,
  onNewProject,
}: {
  projects: { name: string; path: string; current: boolean }[];
  currentProject: string;
  managedProjects: { id: string; name: string; container_status: string }[];
  onSwitch: (path: string) => void;
  onOpenManaged: (id: string) => void;
  onNewProject: () => void;
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
        <div className="absolute left-0 mt-1 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
          <div className="py-1 max-h-80 overflow-y-auto">
            {/* Current Project Section */}
            <div className="px-3 py-1 text-xs text-gray-500 uppercase">Current</div>
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

            {/* Managed Projects Section */}
            {managedProjects.length > 0 && (
              <>
                <div className="border-t border-gray-700 my-1"></div>
                <div className="px-3 py-1 text-xs text-gray-500 uppercase">Isolated Projects</div>
                {managedProjects.map((proj) => (
                  <button
                    key={proj.id}
                    onClick={() => {
                      onOpenManaged(proj.id);
                      setIsOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-gray-700 text-sm flex items-center justify-between"
                  >
                    <span>{proj.name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      proj.container_status === 'running'
                        ? 'bg-green-600/20 text-green-400'
                        : 'bg-gray-600/20 text-gray-400'
                    }`}>
                      {proj.container_status}
                    </span>
                  </button>
                ))}
              </>
            )}

            {/* New Project Button */}
            <div className="border-t border-gray-700 my-1"></div>
            <button
              onClick={() => {
                onNewProject();
                setIsOpen(false);
              }}
              className="w-full text-left px-3 py-2 hover:bg-gray-700 text-sm text-blue-400 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Isolated Project
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// New Project Modal
function NewProjectModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, gitUrl?: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [gitUrl, setGitUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await onCreate(name.trim(), gitUrl.trim() || undefined);
      setName('');
      setGitUrl('');
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New Isolated Project">
      <div className="space-y-4">
        <p className="text-sm text-gray-400">
          Create a new project in its own isolated Docker container.
        </p>

        <div>
          <label className="block text-sm font-medium mb-1">Project Name</label>
          <input
            type="text"
            value={name}
            onInput={(e) => setName((e.target as HTMLInputElement).value)}
            placeholder="my-awesome-project"
            className="w-full bg-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Git URL (optional)</label>
          <input
            type="text"
            value={gitUrl}
            onInput={(e) => setGitUrl((e.target as HTMLInputElement).value)}
            placeholder="https://github.com/user/repo.git"
            className="w-full bg-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Leave empty to create a blank project
          </p>
        </div>

        {error && (
          <div className="text-sm text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-gray-700 rounded-lg hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </div>
    </Modal>
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
