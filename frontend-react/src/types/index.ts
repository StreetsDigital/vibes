// Task/Bead types
export interface Task {
  id: string;
  name: string;
  description?: string;
  status: TaskStatus;
  priority: number;
  test_cases?: string[];
}

export type TaskStatus = 'pending' | 'in_progress' | 'needs_review' | 'passing';

export interface BoardStats {
  total: number;
  pending: number;
  in_progress: number;
  needs_review: number;
  passing: number;
  progress_percent: number;
}

export interface BoardData {
  board: {
    todo: Task[];
    in_progress: Task[];
    review: Task[];
    done: Task[];
  };
  stats: BoardStats;
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant' | 'error';
  content: string;
  timestamp?: string;
}

// Project types
export interface Project {
  name: string;
  path: string;
  current: boolean;
}

// MCP types
export interface McpServer {
  name: string;
  scope: 'global' | 'project';
  command: string;
  args: string[];
  env?: Record<string, string>;
  enabled: boolean;
}

// Skill types
export interface Skill {
  name: string;
  file: string;
  scope: 'global' | 'project';
  description?: string;
  enabled: boolean;
}

// Tool types
export interface Tool {
  name: string;
  description: string;
  details?: string;
  enabled: boolean;
  denied_in?: 'global' | 'project' | null;
}

// Hook types
export interface Hook {
  event: HookEvent;
  command: string;
  scope: 'global' | 'project';
}

export type HookEvent = 'PreToolUse' | 'PostToolUse' | 'Notification' | 'Stop';

// View types
export type ViewType = 'board' | 'chat' | 'tools';
