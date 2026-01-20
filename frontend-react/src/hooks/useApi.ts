import { useState, useCallback } from 'preact/hooks';
import type {
  Task, BoardData, ChatMessage, Project,
  McpServer, Skill, Tool, Hook
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

  const loadHistory = useCallback(async () => {
    const data = await apiFetch<{ messages: ChatMessage[] }>('/chat/history');
    setMessages(data.messages || []);
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    const userMsg: ChatMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await apiFetch<{ response: string }>('/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
      });
      const assistantMsg: ChatMessage = { role: 'assistant', content: data.response };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = { role: 'error', content: 'Error: Could not reach Claude' };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearHistory = useCallback(async () => {
    await apiFetch('/chat/history', { method: 'DELETE' });
    setMessages([]);
  }, []);

  return { messages, loading, loadHistory, sendMessage, clearHistory };
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
