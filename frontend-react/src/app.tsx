import { useState, useEffect } from 'preact/hooks';
import type { ViewType, Task } from './types';
import { useBoard, useChat, useProjects, useGit, useSession, useProjectManager, useSystemHealth } from './hooks/useApi';
import { Board } from './components/Board';
import { Chat } from './components/Chat';
import { ToolsPanel } from './components/ToolsPanel';
import { LogsPanel } from './components/LogsPanel';
import { WorkflowPanel } from './components/WorkflowPanel';
import { Modal } from './components/Modal';

export function App() {
  const [currentView, setCurrentView] = useState<ViewType>('board');
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);

  const board = useBoard();
  const chat = useChat();
  const projects = useProjects();
  const git = useGit();
  const session = useSession();
  const projectManager = useProjectManager();
  const systemHealth = useSystemHealth();

  // Initialize on mount
  useEffect(() => {
    board.refresh();
    chat.loadHistory();
    projects.load();
    git.loadBranch();
    projectManager.loadProjects();
    systemHealth.refresh();
    checkSession();

    // Refresh board every 10 seconds, health every 30 seconds
    const boardInterval = setInterval(board.refresh, 10000);
    const healthInterval = setInterval(systemHealth.refresh, 30000);
    return () => {
      clearInterval(boardInterval);
      clearInterval(healthInterval);
    };
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
      {/* Sticky header + tabs container on desktop */}
      <div className="md:sticky md:top-0 z-50 flex-shrink-0">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
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
              onStartProject={projectManager.startProject}
              onStopProject={projectManager.stopProject}
              onDeleteProject={projectManager.deleteProject}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 hidden sm:inline">
              {board.board?.stats
                ? `${board.board.stats.passing}/${board.board.stats.total} complete (${board.board.stats.progress_percent}%)`
                : 'Loading...'}
            </span>
            {/* Health Indicator */}
            <button
              onClick={() => setShowHealthModal(true)}
              className={`p-2 rounded-lg text-sm flex items-center gap-1 ${
                systemHealth.health?.status === 'healthy'
                  ? 'bg-green-600/20 text-green-400 hover:bg-green-600/30'
                  : systemHealth.health?.status === 'warning'
                  ? 'bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/30'
                  : systemHealth.health?.status === 'critical'
                  ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30 animate-pulse'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
              title={`System: ${systemHealth.health?.status || 'loading'}`}
            >
              <span className={`w-2 h-2 rounded-full ${
                systemHealth.health?.status === 'healthy'
                  ? 'bg-green-400'
                  : systemHealth.health?.status === 'warning'
                  ? 'bg-yellow-400'
                  : systemHealth.health?.status === 'critical'
                  ? 'bg-red-400'
                  : 'bg-gray-400'
              }`}></span>
              <span className="hidden sm:inline text-xs">
                {systemHealth.health
                  ? `${systemHealth.health.memory.percent}%`
                  : '...'}
              </span>
            </button>
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
          active={currentView === 'flow'}
          onClick={() => setCurrentView('flow')}
          label="Flow"
        />
        <TabButton
          active={currentView === 'tools'}
          onClick={() => setCurrentView('tools')}
          label="Tools"
        />
        <TabButton
          active={currentView === 'logs'}
          onClick={() => setCurrentView('logs')}
          label="Logs"
        />
      </div>

      {/* Desktop Tab Bar */}
      <div className="hidden md:flex border-b border-gray-700 bg-gray-800 justify-center">
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
          active={currentView === 'flow'}
          onClick={() => setCurrentView('flow')}
          label="Flow"
        />
        <TabButton
          active={currentView === 'tools'}
          onClick={() => setCurrentView('tools')}
          label="Tools"
        />
        <TabButton
          active={currentView === 'logs'}
          onClick={() => setCurrentView('logs')}
          label="Logs"
        />
      </div>
      </div>{/* End sticky header + tabs container */}

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
            isVisible={currentView === 'chat'}
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

        {/* Logs Panel */}
        <aside
          className={`w-full flex-1 bg-gray-900 flex-col h-full ${
            currentView !== 'logs' ? 'hidden' : 'flex'
          }`}
        >
          <LogsPanel />
        </aside>

        {/* Flow/Workflow Panel */}
        <aside
          className={`w-full flex-1 bg-gray-900 flex-col h-full ${
            currentView !== 'flow' ? 'hidden' : 'flex'
          }`}
        >
          <WorkflowPanel />
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

      {/* Health Modal */}
      <HealthModal
        isOpen={showHealthModal}
        onClose={() => setShowHealthModal(false)}
        health={systemHealth.health}
        onRefresh={systemHealth.refresh}
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
  onStartProject,
  onStopProject,
  onDeleteProject,
}: {
  projects: { name: string; path: string; current: boolean }[];
  currentProject: string;
  managedProjects: { id: string; name: string; container_status: string }[];
  onSwitch: (path: string) => void;
  onOpenManaged: (id: string) => void;
  onNewProject: () => void;
  onStartProject: (id: string) => void;
  onStopProject: (id: string) => void;
  onDeleteProject: (id: string) => void;
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
                  <div
                    key={proj.id}
                    className="px-3 py-2 hover:bg-gray-700 text-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <button
                        onClick={() => {
                          onOpenManaged(proj.id);
                          setIsOpen(false);
                        }}
                        className="text-left flex-1 truncate hover:text-blue-400"
                      >
                        {proj.name}
                      </button>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        proj.container_status === 'running'
                          ? 'bg-green-600/20 text-green-400'
                          : 'bg-gray-600/20 text-gray-400'
                      }`}>
                        {proj.container_status}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {proj.container_status === 'running' ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); onStopProject(proj.id); }}
                          className="p-1 text-yellow-400 hover:bg-yellow-400/20 rounded"
                          title="Stop"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                          </svg>
                        </button>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); onStartProject(proj.id); }}
                          className="p-1 text-green-400 hover:bg-green-400/20 rounded"
                          title="Start"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                          </svg>
                        </button>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenManaged(proj.id); }}
                        className="p-1 text-blue-400 hover:bg-blue-400/20 rounded"
                        title="Open"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Delete project "${proj.name}"?`)) {
                            onDeleteProject(proj.id);
                          }
                        }}
                        className="p-1 text-red-400 hover:bg-red-400/20 rounded"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
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

// Health Modal
import type { SystemHealth } from './hooks/useApi';

function HealthModal({
  isOpen,
  onClose,
  health,
  onRefresh,
}: {
  isOpen: boolean;
  onClose: () => void;
  health: SystemHealth | null;
  onRefresh: () => void;
}) {
  if (!isOpen) return null;

  const statusColor = {
    healthy: 'text-green-400',
    warning: 'text-yellow-400',
    critical: 'text-red-400',
    error: 'text-red-400',
  };

  const ProgressBar = ({ percent, color }: { percent: number; color: string }) => (
    <div className="w-full bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full ${color}`}
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="System Health">
      <div className="space-y-4">
        {!health ? (
          <div className="text-center py-4 text-gray-400">Loading...</div>
        ) : (
          <>
            {/* Status Badge */}
            <div className="flex items-center justify-between">
              <span className={`text-lg font-bold ${statusColor[health.status]}`}>
                {health.status.toUpperCase()}
              </span>
              <button
                onClick={onRefresh}
                className="text-xs text-gray-400 hover:text-white"
              >
                Refresh
              </button>
            </div>

            {/* Warnings */}
            {health.warnings.length > 0 && (
              <div className="bg-yellow-600/10 border border-yellow-600/30 rounded-lg p-3">
                <div className="text-yellow-400 text-sm font-medium mb-1">Warnings</div>
                {health.warnings.map((w, i) => (
                  <div key={i} className="text-yellow-300/80 text-xs">{w}</div>
                ))}
              </div>
            )}

            {/* CPU */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>CPU</span>
                <span className="text-gray-400">
                  {health.cpu.percent}% ({health.cpu.cores} cores)
                </span>
              </div>
              <ProgressBar
                percent={health.cpu.percent}
                color={health.cpu.percent > 80 ? 'bg-red-500' : health.cpu.percent > 60 ? 'bg-yellow-500' : 'bg-green-500'}
              />
              <div className="text-xs text-gray-500 mt-1">
                Load: {health.cpu.load_1m} / {health.cpu.load_5m} / {health.cpu.load_15m}
              </div>
            </div>

            {/* Memory */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Memory</span>
                <span className="text-gray-400">
                  {health.memory.used_gb}GB / {health.memory.total_gb}GB ({health.memory.percent}%)
                </span>
              </div>
              <ProgressBar
                percent={health.memory.percent}
                color={health.memory.percent > 85 ? 'bg-red-500' : health.memory.percent > 70 ? 'bg-yellow-500' : 'bg-green-500'}
              />
            </div>

            {/* Disk */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Disk</span>
                <span className="text-gray-400">
                  {health.disk.used_gb}GB / {health.disk.total_gb}GB ({health.disk.percent}%)
                </span>
              </div>
              <ProgressBar
                percent={health.disk.percent}
                color={health.disk.percent > 90 ? 'bg-red-500' : health.disk.percent > 80 ? 'bg-yellow-500' : 'bg-green-500'}
              />
            </div>

            {/* Containers */}
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Containers</span>
                <span className="text-gray-400">
                  {health.containers.running} / {health.containers.total} running
                </span>
              </div>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {health.containers.list.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-gray-800 rounded px-2 py-1">
                    <span className="truncate">{c.name}</span>
                    <span className={`px-1.5 py-0.5 rounded ${
                      c.status === 'running'
                        ? 'bg-green-600/20 text-green-400'
                        : 'bg-gray-600/20 text-gray-400'
                    }`}>
                      {c.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Timestamp */}
            <div className="text-xs text-gray-500 text-center">
              Last updated: {new Date(health.timestamp).toLocaleTimeString()}
            </div>
          </>
        )}
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
