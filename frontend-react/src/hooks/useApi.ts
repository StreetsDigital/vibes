import { useState, useCallback, useRef, useEffect } from 'preact/hooks';
import type {
  Task, BoardData, ChatMessage, Project,
  McpServer, Skill, Tool, Hook, AgentData, LogEntry
} from '../types';

const API_BASE = '/api';

// Generic fetch wrapper
async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  return response.json();
}

// Board API
export function useBoard() {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<BoardData>('/board');
      setBoard(data);
    } finally {
      setLoading(false);
    }
  }, []);

  const createTask = useCallback(async (task: Partial<Task>) => {
    await apiFetch('/task', {
      method: 'POST',
      body: JSON.stringify(task),
    });
    await refresh();
  }, [refresh]);

  const moveTask = useCallback(async (taskId: string, status: string) => {
    await apiFetch(`/task/${taskId}/move`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
    await refresh();
  }, [refresh]);

  return { board, loading, refresh, createTask, moveTask };
}

// Chat API
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    const data = await apiFetch<{ messages: ChatMessage[] }>('/chat/history');
    setMessages(data.messages || []);
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    const userMsg: ChatMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    // Create new abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });
      const data = await response.json();
      const assistantMsg: ChatMessage = { role: 'assistant', content: data.response };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        const stoppedMsg: ChatMessage = { role: 'assistant', content: '*(Stopped)*' };
        setMessages(prev => [...prev, stoppedMsg]);
      } else {
        const errorMsg: ChatMessage = { role: 'error', content: 'Error: Could not reach Claude' };
        setMessages(prev => [...prev, errorMsg]);
      }
    } finally {
      setLoading(false);
      setAbortController(null);
    }
  }, []);

  const stopGeneration = useCallback(() => {
    if (abortController) {
      abortController.abort();
      // Also notify the server to stop any ongoing processing
      fetch(`${API_BASE}/chat/stop`, { method: 'POST' }).catch(() => {});
    }
  }, [abortController]);

  const clearHistory = useCallback(async () => {
    await apiFetch('/chat/history', { method: 'DELETE' });
    setMessages([]);
  }, []);

  return { messages, loading, loadHistory, sendMessage, stopGeneration, clearHistory };
}

// Projects API
export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<string>('');

  const load = useCallback(async () => {
    const data = await apiFetch<{ projects: Project[] }>('/projects');
    setProjects(data.projects || []);
    const current = data.projects?.find(p => p.current);
    if (current) setCurrentProject(current.name);
  }, []);

  const switchProject = useCallback(async (path: string) => {
    const data = await apiFetch<{ success: boolean; project: string }>('/projects/switch', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
    if (data.success) {
      setCurrentProject(data.project);
    }
    return data.success;
  }, []);

  return { projects, currentProject, load, switchProject };
}

// MCP Servers API
export function useMcpServers() {
  const [servers, setServers] = useState<McpServer[]>([]);

  const load = useCallback(async () => {
    const data = await apiFetch<{ servers: McpServer[] }>('/claude/mcp');
    setServers(data.servers || []);
  }, []);

  const add = useCallback(async (server: Partial<McpServer>) => {
    await apiFetch('/claude/mcp', {
      method: 'POST',
      body: JSON.stringify(server),
    });
    await load();
  }, [load]);

  const update = useCallback(async (name: string, updates: Partial<McpServer>) => {
    await apiFetch(`/claude/mcp/${name}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    await load();
  }, [load]);

  const remove = useCallback(async (name: string, scope: string) => {
    await apiFetch(`/claude/mcp/${name}`, {
      method: 'DELETE',
      body: JSON.stringify({ scope }),
    });
    await load();
  }, [load]);

  const toggle = useCallback(async (name: string, scope: string, enabled: boolean) => {
    await apiFetch(`/claude/mcp/${name}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ scope, enabled }),
    });
    await load();
  }, [load]);

  const getOne = useCallback(async (name: string, scope: string): Promise<McpServer | null> => {
    try {
      return await apiFetch<McpServer>(`/claude/mcp/${name}?scope=${scope}`);
    } catch {
      return null;
    }
  }, []);

  return { servers, load, add, update, remove, toggle, getOne };
}

// Skills API
export function useSkills() {
  const [skills, setSkills] = useState<Skill[]>([]);

  const load = useCallback(async () => {
    const data = await apiFetch<{ skills: Skill[] }>('/claude/skills');
    setSkills(data.skills || []);
  }, []);

  const create = useCallback(async (skill: {
    name: string;
    description?: string;
    trigger?: string;
    solution?: string;
    scope?: string;
  }) => {
    await apiFetch('/claude/skills', {
      method: 'POST',
      body: JSON.stringify(skill),
    });
    await load();
  }, [load]);

  const getContent = useCallback(async (filePath: string): Promise<string> => {
    const data = await apiFetch<{ content: string }>(`/claude/skills${filePath}`);
    return data.content || '';
  }, []);

  const updateContent = useCallback(async (filePath: string, content: string) => {
    await apiFetch(`/claude/skills${filePath}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
    await load();
  }, [load]);

  const remove = useCallback(async (filePath: string) => {
    await apiFetch(`/claude/skills${filePath}`, { method: 'DELETE' });
    await load();
  }, [load]);

  return { skills, load, create, getContent, updateContent, remove };
}

// Tools API
export function useTools() {
  const [tools, setTools] = useState<Tool[]>([]);

  const load = useCallback(async () => {
    const data = await apiFetch<{ tools: Tool[] }>('/claude/tools');
    setTools(data.tools || []);
  }, []);

  const toggle = useCallback(async (name: string, enabled: boolean) => {
    await apiFetch(`/claude/tools/${name}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled, scope: 'project' }),
    });
    await load();
  }, [load]);

  const getDetails = useCallback(async (name: string): Promise<Tool | null> => {
    try {
      return await apiFetch<Tool>(`/claude/tools/${name}`);
    } catch {
      return null;
    }
  }, []);

  return { tools, load, toggle, getDetails };
}

// Hooks API
export function useHooks() {
  const [hooks, setHooks] = useState<Hook[]>([]);

  const load = useCallback(async () => {
    const data = await apiFetch<{ hooks: Hook[] }>('/claude/hooks');
    setHooks(data.hooks || []);
  }, []);

  const add = useCallback(async (hook: Partial<Hook>) => {
    await apiFetch('/claude/hooks', {
      method: 'POST',
      body: JSON.stringify(hook),
    });
    await load();
  }, [load]);

  const update = useCallback(async (
    oldHook: { event: string; command: string; scope: string },
    newHook: { event: string; command: string; scope: string }
  ) => {
    await apiFetch('/claude/hooks', {
      method: 'PUT',
      body: JSON.stringify({
        old_event: oldHook.event,
        old_command: oldHook.command,
        old_scope: oldHook.scope,
        event: newHook.event,
        command: newHook.command,
        scope: newHook.scope,
      }),
    });
    await load();
  }, [load]);

  const remove = useCallback(async (event: string, command: string, scope: string) => {
    await apiFetch('/claude/hooks', {
      method: 'DELETE',
      body: JSON.stringify({ event, command, scope }),
    });
    await load();
  }, [load]);

  return { hooks, load, add, update, remove };
}

// Git API
export function useGit() {
  const [branch, setBranch] = useState('main');

  const loadBranch = useCallback(async () => {
    const data = await apiFetch<{ branch: string }>('/git/branch');
    setBranch(data.branch || 'main');
  }, []);

  return { branch, loadBranch };
}

// Session API
export function useSession() {
  const ping = useCallback(async () => {
    const data = await apiFetch<{ hours_inactive: number; summary?: string }>('/session/ping', {
      method: 'POST',
    });
    return data;
  }, []);

  return { ping };
}

// Project Manager API (isolated containers)
export interface ManagedProject {
  id: string;
  name: string;
  port: number;
  git_url?: string;
  created_at: string;
  container_status: string;
  path: string;
}

export function useProjectManager() {
  const [managedProjects, setManagedProjects] = useState<ManagedProject[]>([]);
  const [loading, setLoading] = useState(false);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/manager/projects');
      const data = await response.json();
      setManagedProjects(data.projects || []);
    } catch (error) {
      console.error('Failed to load managed projects:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const createProject = useCallback(async (name: string, gitUrl?: string) => {
    const response = await fetch('/api/manager/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, git_url: gitUrl }),
    });
    const data = await response.json();
    if (data.success) {
      await loadProjects();
    }
    return data;
  }, [loadProjects]);

  const deleteProject = useCallback(async (projectId: string) => {
    const response = await fetch(`/api/manager/projects/${projectId}`, {
      method: 'DELETE',
    });
    const data = await response.json();
    if (data.success) {
      await loadProjects();
    }
    return data;
  }, [loadProjects]);

  const startProject = useCallback(async (projectId: string) => {
    const response = await fetch(`/api/manager/projects/${projectId}/start`, {
      method: 'POST',
    });
    const data = await response.json();
    await loadProjects();
    return data;
  }, [loadProjects]);

  const stopProject = useCallback(async (projectId: string) => {
    const response = await fetch(`/api/manager/projects/${projectId}/stop`, {
      method: 'POST',
    });
    const data = await response.json();
    await loadProjects();
    return data;
  }, [loadProjects]);

  const openProject = useCallback((projectId: string) => {
    // Open project in new tab
    window.open(`/project/${projectId}/`, '_blank');
  }, []);

  const updateProject = useCallback(async (projectId: string, updates: { name?: string; git_url?: string }) => {
    const response = await fetch(`/api/manager/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    const data = await response.json();
    if (data.success) {
      await loadProjects();
    }
    return data;
  }, [loadProjects]);

  return {
    managedProjects,
    loading,
    loadProjects,
    createProject,
    deleteProject,
    startProject,
    stopProject,
    openProject,
    updateProject,
  };
}

// Agents API
export function useAgents() {
  const [agents, setAgents] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AgentData>('/agents');
      setAgents(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { agents, loading, error, load };
}

// System Health API
export interface SystemHealth {
  status: 'healthy' | 'warning' | 'critical' | 'error';
  warnings: string[];
  cpu: {
    percent: number;
    cores: number;
    load_1m: number;
    load_5m: number;
    load_15m: number;
  };
  memory: {
    total_gb: number;
    used_gb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    percent: number;
  };
  containers: {
    total: number;
    running: number;
    list: { name: string; status: string; image: string }[];
  };
  timestamp: string;
}

export function useSystemHealth() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/manager/health/system');
      if (!response.ok) throw new Error('Failed to fetch health');
      const data = await response.json();
      setHealth(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { health, loading, error, refresh };
}

// Logs API
export type LogFilter = 'all' | 'claude' | 'system' | 'error';

export function useLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogFilter>('all');
  const [loading, setLoading] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [polling, setPolling] = useState(false);
  const pollIntervalRef = useRef<number | null>(null);

  const load = useCallback(async (filterType?: LogFilter) => {
    setLoading(true);
    try {
      const f = filterType ?? filter;
      const data = await apiFetch<{ logs: LogEntry[] }>(`/logs?filter=${f}`);
      setLogs(data.logs || []);
    } catch (e) {
      console.error('Failed to load logs:', e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const clear = useCallback(async () => {
    try {
      await apiFetch('/logs', { method: 'DELETE' });
      setLogs([]);
    } catch (e) {
      console.error('Failed to clear logs:', e);
    }
  }, []);

  const changeFilter = useCallback((newFilter: LogFilter) => {
    setFilter(newFilter);
    load(newFilter);
  }, [load]);

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;
    setPolling(true);
    pollIntervalRef.current = window.setInterval(() => {
      load();
    }, 2000);
  }, [load]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setPolling(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return {
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
  };
}
