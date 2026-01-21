import { useState, useEffect } from 'preact/hooks';
import { Toggle } from './Toggle';
import { Modal } from './Modal';
import { ConfigHelper } from './ConfigHelper';
import type { McpServer, Skill, Tool, Hook, HookEvent } from '../types';
import { useMcpServers, useSkills, useTools, useHooks, useAgents } from '../hooks/useApi';

export function ToolsPanel() {
  const mcpApi = useMcpServers();
  const skillsApi = useSkills();
  const toolsApi = useTools();
  const hooksApi = useHooks();
  const agentsApi = useAgents();

  // Modals
  const [showAddMcp, setShowAddMcp] = useState(false);
  const [showAddSkill, setShowAddSkill] = useState(false);
  const [showAddHook, setShowAddHook] = useState(false);
  const [showConfigHelper, setShowConfigHelper] = useState(false);
  const [selectedMcp, setSelectedMcp] = useState<McpServer | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<{ skill: Skill; content: string } | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [selectedHook, setSelectedHook] = useState<Hook | null>(null);

  // Quick Actions state
  const [actionStates, setActionStates] = useState<Record<string, 'idle' | 'loading' | 'success' | 'error'>>({});
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});

  // Forms
  const [mcpForm, setMcpForm] = useState<{ name: string; command: string; args: string; scope: 'project' | 'global' }>({ name: '', command: '', args: '', scope: 'project' });
  const [skillForm, setSkillForm] = useState<{ name: string; description: string; trigger: string; solution: string; scope: 'project' | 'global' }>({ name: '', description: '', trigger: '', solution: '', scope: 'project' });
  const [hookForm, setHookForm] = useState<{ event: HookEvent; command: string; scope: 'project' | 'global' }>({ event: 'PreToolUse', command: '', scope: 'project' });

  // Load data on mount
  useEffect(() => {
    mcpApi.load();
    skillsApi.load();
    toolsApi.load();
    hooksApi.load();
    agentsApi.load();
  }, []);

  // Add MCP
  const handleAddMcp = async (e: Event) => {
    e.preventDefault();
    await mcpApi.add({
      name: mcpForm.name,
      command: mcpForm.command,
      args: mcpForm.args.split(' ').filter(a => a),
      scope: mcpForm.scope,
    });
    setMcpForm({ name: '', command: '', args: '', scope: 'project' });
    setShowAddMcp(false);
  };

  // View MCP
  const handleViewMcp = async (server: McpServer) => {
    const details = await mcpApi.getOne(server.name, server.scope);
    if (details) setSelectedMcp(details);
  };

  // Update MCP
  const handleUpdateMcp = async (e: Event) => {
    e.preventDefault();
    if (!selectedMcp) return;
    await mcpApi.update(selectedMcp.name, selectedMcp);
    setSelectedMcp(null);
  };

  // Delete MCP
  const handleDeleteMcp = async () => {
    if (!selectedMcp || !confirm(`Delete MCP server "${selectedMcp.name}"?`)) return;
    await mcpApi.remove(selectedMcp.name, selectedMcp.scope);
    setSelectedMcp(null);
  };

  // Add Skill
  const handleAddSkill = async (e: Event) => {
    e.preventDefault();
    await skillsApi.create(skillForm);
    setSkillForm({ name: '', description: '', trigger: '', solution: '', scope: 'project' });
    setShowAddSkill(false);
  };

  // View Skill
  const handleViewSkill = async (skill: Skill) => {
    const content = await skillsApi.getContent(skill.file);
    setSelectedSkill({ skill, content });
  };

  // Update Skill
  const handleUpdateSkill = async (e: Event) => {
    e.preventDefault();
    if (!selectedSkill) return;
    await skillsApi.updateContent(selectedSkill.skill.file, selectedSkill.content);
    setSelectedSkill(null);
  };

  // Delete Skill
  const handleDeleteSkill = async () => {
    if (!selectedSkill || !confirm(`Delete skill "${selectedSkill.skill.name}"?`)) return;
    await skillsApi.remove(selectedSkill.skill.file);
    setSelectedSkill(null);
  };

  // View Tool
  const handleViewTool = async (tool: Tool) => {
    const details = await toolsApi.getDetails(tool.name);
    if (details) setSelectedTool(details);
  };

  // Add Hook
  const handleAddHook = async (e: Event) => {
    e.preventDefault();
    await hooksApi.add(hookForm);
    setHookForm({ event: 'PreToolUse', command: '', scope: 'project' });
    setShowAddHook(false);
  };

  // View Hook
  const handleViewHook = (hook: Hook) => {
    setSelectedHook(hook);
  };

  // Delete Hook
  const handleDeleteHook = async () => {
    if (!selectedHook || !confirm(`Delete hook "${selectedHook.event}"?`)) return;
    await hooksApi.remove(selectedHook.event, selectedHook.command, selectedHook.scope);
    setSelectedHook(null);
  };

  // Quick Actions handlers
  const executeQuickAction = async (actionName: string, action: () => Promise<void>) => {
    setActionStates(prev => ({ ...prev, [actionName]: 'loading' }));
    setActionErrors(prev => ({ ...prev, [actionName]: '' }));

    try {
      await action();
      setActionStates(prev => ({ ...prev, [actionName]: 'success' }));
      // Clear success state after 3 seconds
      setTimeout(() => {
        setActionStates(prev => ({ ...prev, [actionName]: 'idle' }));
      }, 3000);
    } catch (error) {
      setActionStates(prev => ({ ...prev, [actionName]: 'error' }));
      setActionErrors(prev => ({ ...prev, [actionName]: (error as Error).message }));
      // Clear error state after 5 seconds
      setTimeout(() => {
        setActionStates(prev => ({ ...prev, [actionName]: 'idle' }));
        setActionErrors(prev => ({ ...prev, [actionName]: '' }));
      }, 5000);
    }
  };

  const handleCommitChanges = () => {
    executeQuickAction('commit', async () => {
      const response = await fetch('/api/skills/commit', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to commit changes');
    });
  };

  const handleCreatePR = () => {
    executeQuickAction('pr', async () => {
      const response = await fetch('/api/git/create-pr', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to create PR');
    });
  };

  const handleRunQualityChecks = () => {
    executeQuickAction('quality', async () => {
      const response = await fetch('/api/quality/check', { method: 'POST' });
      if (!response.ok) throw new Error('Quality checks failed');
    });
  };

  const handleExtractLearnings = () => {
    executeQuickAction('retrospective', async () => {
      const response = await fetch('/api/skills/retrospective', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to extract learnings');
    });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-4 border-b border-gray-700">
        <h2 className="font-semibold text-gray-300">Claude Tools</h2>
        <p className="text-xs text-gray-500">MCP servers, skills, and settings</p>
      </div>

      {/* MCP Servers */}
      <Section
        title="MCP Servers"
        onAdd={() => setShowAddMcp(true)}
        isEmpty={mcpApi.servers.length === 0}
        emptyText="No MCP servers configured"
      >
        {mcpApi.servers.map(server => (
          <ListItem
            key={`${server.scope}-${server.name}`}
            title={server.name}
            subtitle={`${server.scope} • ${server.command}`}
            checked={server.enabled}
            onToggle={(enabled) => mcpApi.toggle(server.name, server.scope, enabled)}
            onClick={() => handleViewMcp(server)}
          />
        ))}
      </Section>

      {/* Skills */}
      <Section
        title="Skills"
        onAdd={() => setShowAddSkill(true)}
        isEmpty={skillsApi.skills.length === 0}
        emptyText="No skills created yet"
      >
        {skillsApi.skills.map(skill => (
          <div
            key={skill.file}
            className="p-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700"
            onClick={() => handleViewSkill(skill)}
          >
            <div className="text-sm font-medium">{skill.name}</div>
            <div className="text-xs text-gray-500">{skill.description || skill.scope}</div>
          </div>
        ))}
      </Section>

      {/* Built-in Tools */}
      <Section title="Built-in Tools" isEmpty={toolsApi.tools.length === 0}>
        {toolsApi.tools.map(tool => (
          <ListItem
            key={tool.name}
            title={tool.name}
            subtitle={tool.description}
            checked={tool.enabled}
            onToggle={(enabled) => toolsApi.toggle(tool.name, enabled)}
            onClick={() => handleViewTool(tool)}
          />
        ))}
      </Section>

      {/* Hooks */}
      <Section
        title="Hooks"
        onAdd={() => setShowAddHook(true)}
        isEmpty={hooksApi.hooks.length === 0}
        emptyText="No hooks configured"
      >
        {hooksApi.hooks.map((hook, i) => (
          <div
            key={i}
            className="flex items-center justify-between p-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700"
            onClick={() => handleViewHook(hook)}
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{hook.event}</div>
              <div className="text-xs text-gray-500 truncate">{hook.scope} • {hook.command}</div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); hooksApi.remove(hook.event, hook.command, hook.scope); }}
              className="ml-2 p-1 text-red-400 hover:text-red-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </Section>

      {/* Agents */}
      <Section title="Agents" isEmpty={!agentsApi.agents || (agentsApi.agents.subagents.length === 0 && agentsApi.agents.polecats.length === 0 && agentsApi.agents.containers.length === 0)} emptyText="No active agents">
        {agentsApi.agents && (
          <div className="space-y-2">
            {/* Subagents */}
            {agentsApi.agents.subagents.map(agent => (
              <div key={agent.id} className="p-2 bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{agent.feature_name || agent.id}</div>
                    <div className="text-xs text-gray-500">Subagent • {Math.round(agent.duration)}s • {agent.status}</div>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${
                    agent.status === 'running' ? 'bg-green-400' :
                    agent.status === 'complete' ? 'bg-blue-400' : 'bg-yellow-400'
                  }`}></div>
                </div>
              </div>
            ))}

            {/* Polecats */}
            {agentsApi.agents.polecats.map(polecat => (
              <div key={polecat.id} className="p-2 bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">Polecat {polecat.id}</div>
                    <div className="text-xs text-gray-500">Machine {polecat.machine_id} • Convoy {polecat.convoy_id}</div>
                  </div>
                  <div className="text-xs text-gray-400">{polecat.status}</div>
                </div>
              </div>
            ))}

            {/* Container Agents */}
            {agentsApi.agents.containers.map(container => (
              <div key={container.name} className="p-2 bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{container.name}</div>
                    <div className="text-xs text-gray-500">Container • Project {container.project_id}</div>
                  </div>
                  <div className="text-xs text-gray-400">{container.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {agentsApi.loading && <div className="text-sm text-gray-500">Loading agents...</div>}
        {agentsApi.error && <div className="text-sm text-red-400">Error: {agentsApi.error}</div>}
      </Section>

      {/* Quick Actions */}
      <div className="p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <QuickActionWithState
            onClick={handleCommitChanges}
            label="Commit changes"
            state={actionStates.commit || 'idle'}
            error={actionErrors.commit}
          />
          <QuickActionWithState
            onClick={handleCreatePR}
            label="Create PR"
            state={actionStates.pr || 'idle'}
            error={actionErrors.pr}
          />
          <QuickActionWithState
            onClick={handleRunQualityChecks}
            label="Run quality checks"
            state={actionStates.quality || 'idle'}
            error={actionErrors.quality}
          />
          <QuickActionWithState
            onClick={handleExtractLearnings}
            label="Extract learnings"
            state={actionStates.retrospective || 'idle'}
            error={actionErrors.retrospective}
          />
          <button
            onClick={() => setShowConfigHelper(true)}
            className="w-full text-left px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 text-sm flex items-center justify-between"
          >
            <span>Configuration Helper</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Add MCP Modal */}
      <Modal isOpen={showAddMcp} onClose={() => setShowAddMcp(false)} title="Add MCP Server">
        <form onSubmit={handleAddMcp}>
          <FormFields>
            <FormField label="Name">
              <input
                type="text"
                value={mcpForm.name}
                onInput={(e) => setMcpForm({ ...mcpForm, name: (e.target as HTMLInputElement).value })}
                required
                placeholder="my-server"
                className="form-input"
              />
            </FormField>
            <FormField label="Command">
              <input
                type="text"
                value={mcpForm.command}
                onInput={(e) => setMcpForm({ ...mcpForm, command: (e.target as HTMLInputElement).value })}
                required
                placeholder="npx"
                className="form-input"
              />
            </FormField>
            <FormField label="Arguments (space separated)">
              <input
                type="text"
                value={mcpForm.args}
                onInput={(e) => setMcpForm({ ...mcpForm, args: (e.target as HTMLInputElement).value })}
                placeholder="-y @modelcontextprotocol/server-github"
                className="form-input"
              />
            </FormField>
            <FormField label="Scope">
              <select
                value={mcpForm.scope}
                onChange={(e) => setMcpForm({ ...mcpForm, scope: (e.target as HTMLSelectElement).value as 'project' | 'global' })}
                className="form-input"
              >
                <option value="project">Project</option>
                <option value="global">Global</option>
              </select>
            </FormField>
          </FormFields>
          <ModalButtons onCancel={() => setShowAddMcp(false)} submitLabel="Add" />
        </form>
      </Modal>

      {/* View MCP Modal */}
      <Modal isOpen={!!selectedMcp} onClose={() => setSelectedMcp(null)} title="MCP Server">
        {selectedMcp && (
          <form onSubmit={handleUpdateMcp}>
            <FormFields>
              <FormField label="Name">
                <input
                  type="text"
                  value={selectedMcp.name}
                  onInput={(e) => setSelectedMcp({ ...selectedMcp, name: (e.target as HTMLInputElement).value })}
                  className="form-input"
                />
              </FormField>
              <FormField label="Command">
                <input
                  type="text"
                  value={selectedMcp.command}
                  onInput={(e) => setSelectedMcp({ ...selectedMcp, command: (e.target as HTMLInputElement).value })}
                  className="form-input"
                />
              </FormField>
              <FormField label="Arguments">
                <input
                  type="text"
                  value={selectedMcp.args.join(' ')}
                  onInput={(e) => setSelectedMcp({ ...selectedMcp, args: (e.target as HTMLInputElement).value.split(' ').filter(a => a) })}
                  className="form-input"
                />
              </FormField>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Enabled</span>
                <Toggle
                  checked={selectedMcp.enabled}
                  onChange={(enabled) => setSelectedMcp({ ...selectedMcp, enabled })}
                />
              </div>
              <div className="text-xs text-gray-500">Scope: {selectedMcp.scope}</div>
            </FormFields>
            <ModalButtons
              onCancel={() => setSelectedMcp(null)}
              onDelete={handleDeleteMcp}
              submitLabel="Save"
            />
          </form>
        )}
      </Modal>

      {/* Add Skill Modal */}
      <Modal isOpen={showAddSkill} onClose={() => setShowAddSkill(false)} title="Create Skill">
        <form onSubmit={handleAddSkill}>
          <FormFields>
            <FormField label="Name">
              <input
                type="text"
                value={skillForm.name}
                onInput={(e) => setSkillForm({ ...skillForm, name: (e.target as HTMLInputElement).value })}
                required
                placeholder="fix-common-error"
                className="form-input"
              />
            </FormField>
            <FormField label="Description">
              <input
                type="text"
                value={skillForm.description}
                onInput={(e) => setSkillForm({ ...skillForm, description: (e.target as HTMLInputElement).value })}
                placeholder="What this skill does"
                className="form-input"
              />
            </FormField>
            <FormField label="Trigger (when to use)">
              <textarea
                value={skillForm.trigger}
                onInput={(e) => setSkillForm({ ...skillForm, trigger: (e.target as HTMLTextAreaElement).value })}
                rows={2}
                placeholder="When error X occurs..."
                className="form-input"
              />
            </FormField>
            <FormField label="Solution">
              <textarea
                value={skillForm.solution}
                onInput={(e) => setSkillForm({ ...skillForm, solution: (e.target as HTMLTextAreaElement).value })}
                rows={4}
                placeholder="Steps to fix..."
                className="form-input"
              />
            </FormField>
          </FormFields>
          <ModalButtons onCancel={() => setShowAddSkill(false)} submitLabel="Create" />
        </form>
      </Modal>

      {/* View Skill Modal */}
      <Modal isOpen={!!selectedSkill} onClose={() => setSelectedSkill(null)} title={selectedSkill?.skill.name || ''}>
        {selectedSkill && (
          <form onSubmit={handleUpdateSkill}>
            <FormFields>
              <FormField label="Content">
                <textarea
                  value={selectedSkill.content}
                  onInput={(e) => setSelectedSkill({ ...selectedSkill, content: (e.target as HTMLTextAreaElement).value })}
                  rows={12}
                  className="form-input font-mono text-sm"
                />
              </FormField>
              <div className="text-xs text-gray-500">Path: {selectedSkill.skill.file}</div>
            </FormFields>
            <ModalButtons
              onCancel={() => setSelectedSkill(null)}
              onDelete={handleDeleteSkill}
              submitLabel="Save"
            />
          </form>
        )}
      </Modal>

      {/* View Tool Modal */}
      <Modal isOpen={!!selectedTool} onClose={() => setSelectedTool(null)} title={selectedTool?.name || ''}>
        {selectedTool && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Description</label>
              <p className="text-sm">{selectedTool.description}</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Details</label>
              <p className="text-sm text-gray-300">{selectedTool.details || 'No additional details available.'}</p>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
              <span className="text-sm">Enabled</span>
              <Toggle
                checked={selectedTool.enabled}
                onChange={(enabled) => {
                  toolsApi.toggle(selectedTool.name, enabled);
                  setSelectedTool({ ...selectedTool, enabled });
                }}
              />
            </div>
            {selectedTool.denied_in && (
              <div className="text-xs text-yellow-400">
                Disabled in {selectedTool.denied_in} settings
              </div>
            )}
            <button
              onClick={() => setSelectedTool(null)}
              className="w-full px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        )}
      </Modal>

      {/* Add Hook Modal */}
      <Modal isOpen={showAddHook} onClose={() => setShowAddHook(false)} title="Add Hook">
        <form onSubmit={handleAddHook}>
          <FormFields>
            <FormField label="Event">
              <select
                value={hookForm.event}
                onChange={(e) => setHookForm({ ...hookForm, event: (e.target as HTMLSelectElement).value as HookEvent })}
                className="form-input"
              >
                <option value="PreToolUse">PreToolUse - Before tool runs</option>
                <option value="PostToolUse">PostToolUse - After tool runs</option>
                <option value="Notification">Notification - On notifications</option>
                <option value="Stop">Stop - When Claude stops</option>
              </select>
            </FormField>
            <FormField label="Command">
              <input
                type="text"
                value={hookForm.command}
                onInput={(e) => setHookForm({ ...hookForm, command: (e.target as HTMLInputElement).value })}
                required
                placeholder="npm run lint"
                className="form-input"
              />
            </FormField>
            <FormField label="Scope">
              <select
                value={hookForm.scope}
                onChange={(e) => setHookForm({ ...hookForm, scope: (e.target as HTMLSelectElement).value as 'project' | 'global' })}
                className="form-input"
              >
                <option value="project">Project</option>
                <option value="global">Global</option>
              </select>
            </FormField>
          </FormFields>
          <ModalButtons onCancel={() => setShowAddHook(false)} submitLabel="Add" />
        </form>
      </Modal>

      {/* View Hook Modal */}
      <Modal isOpen={!!selectedHook} onClose={() => setSelectedHook(null)} title="Hook">
        {selectedHook && (
          <div className="space-y-4">
            <FormField label="Event">
              <p className="text-sm">{selectedHook.event}</p>
            </FormField>
            <FormField label="Command">
              <p className="text-sm font-mono bg-gray-700 p-2 rounded">{selectedHook.command}</p>
            </FormField>
            <FormField label="Scope">
              <p className="text-sm">{selectedHook.scope}</p>
            </FormField>
            <ModalButtons
              onCancel={() => setSelectedHook(null)}
              onDelete={handleDeleteHook}
              submitLabel=""
            />
          </div>
        )}
      </Modal>

      {/* Configuration Helper */}
      <ConfigHelper
        isOpen={showConfigHelper}
        onClose={() => setShowConfigHelper(false)}
      />
    </div>
  );
}

// Helper Components
function Section({ title, onAdd, isEmpty, emptyText, children }: {
  title: string;
  onAdd?: () => void;
  isEmpty?: boolean;
  emptyText?: string;
  children?: preact.ComponentChildren;
}) {
  return (
    <div className="p-4 border-b border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        {onAdd && (
          <button
            onClick={onAdd}
            className="text-xs px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
          >
            + Add
          </button>
        )}
      </div>
      <div className="space-y-2">
        {isEmpty ? (
          <div className="text-sm text-gray-500">{emptyText}</div>
        ) : children}
      </div>
    </div>
  );
}

function ListItem({ title, subtitle, checked, onToggle, onClick }: {
  title: string;
  subtitle: string;
  checked: boolean;
  onToggle: (checked: boolean) => void;
  onClick: () => void;
}) {
  return (
    <div className="flex items-center justify-between p-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700">
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="text-sm font-medium truncate">{title}</div>
        <div className="text-xs text-gray-500">{subtitle}</div>
      </div>
      <div onClick={(e) => e.stopPropagation()}>
        <Toggle checked={checked} onChange={onToggle} />
      </div>
    </div>
  );
}

function _QuickAction({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 text-sm"
    >
      {label}
    </button>
  );
}
void _QuickAction; // Suppress unused warning

function QuickActionWithState({
  onClick,
  label,
  state,
  error
}: {
  onClick: () => void;
  label: string;
  state: 'idle' | 'loading' | 'success' | 'error';
  error?: string;
}) {
  const getStateIcon = () => {
    switch (state) {
      case 'loading':
        return (
          <svg className="w-4 h-4 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case 'success':
        return (
          <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getButtonColor = () => {
    switch (state) {
      case 'success':
        return 'bg-green-800/20 hover:bg-green-700/30 border border-green-600/30';
      case 'error':
        return 'bg-red-800/20 hover:bg-red-700/30 border border-red-600/30';
      default:
        return 'bg-gray-800 hover:bg-gray-700';
    }
  };

  return (
    <div>
      <button
        onClick={onClick}
        disabled={state === 'loading'}
        className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between ${getButtonColor()}`}
      >
        <span>{label}</span>
        {getStateIcon()}
      </button>
      {state === 'error' && error && (
        <div className="mt-1 px-3 py-1 text-xs text-red-400 bg-red-900/20 rounded">
          {error}
        </div>
      )}
    </div>
  );
}

function FormFields({ children }: { children: preact.ComponentChildren }) {
  return <div className="space-y-4">{children}</div>;
}

function FormField({ label, children }: { label: string; children: preact.ComponentChildren }) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ModalButtons({ onCancel, onDelete, submitLabel }: {
  onCancel: () => void;
  onDelete?: () => void;
  submitLabel: string;
}) {
  return (
    <div className="flex gap-2 mt-6">
      {onDelete && (
        <button
          type="button"
          onClick={onDelete}
          className="px-4 py-3 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30"
        >
          Delete
        </button>
      )}
      <button
        type="button"
        onClick={onCancel}
        className="flex-1 px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
      >
        Cancel
      </button>
      {submitLabel && (
        <button
          type="submit"
          className="flex-1 px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500"
        >
          {submitLabel}
        </button>
      )}
    </div>
  );
}
