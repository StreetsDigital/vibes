import { useState, useEffect } from 'preact/hooks';
import { Toggle } from './Toggle';
import { Modal } from './Modal';
import type { McpServer, Skill, Tool, Hook, HookEvent } from '../types';
import { useMcpServers, useSkills, useTools, useHooks } from '../hooks/useApi';

// Agent types
interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  mcps: string[];
  prompt_prefix: string;
}

interface RecommendedMcp {
  name: string;
  description: string;
  command: string;
  args: string[];
  source?: string;
  installed: boolean;
}

export function ToolsPanel() {
  const mcpApi = useMcpServers();
  const skillsApi = useSkills();
  const toolsApi = useTools();
  const hooksApi = useHooks();

  // Agents state
  const [agentTemplates, setAgentTemplates] = useState<AgentTemplate[]>([]);
  const [recommendedMcps, setRecommendedMcps] = useState<RecommendedMcp[]>([]);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [agentPrompt, setAgentPrompt] = useState('');
  const [agentLoading, setAgentLoading] = useState(false);
  const [showRecommendedMcps, setShowRecommendedMcps] = useState(false);

  // Quick actions state
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<{ action: string; response: string } | null>(null);

  // Modals
  const [showAddMcp, setShowAddMcp] = useState(false);
  const [showAddSkill, setShowAddSkill] = useState(false);
  const [showAddHook, setShowAddHook] = useState(false);
  const [selectedMcp, setSelectedMcp] = useState<McpServer | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<{ skill: Skill; content: string } | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [selectedHook, setSelectedHook] = useState<Hook | null>(null);

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
    loadAgents();
    loadRecommendedMcps();
  }, []);

  // Load agents
  const loadAgents = async () => {
    try {
      const response = await fetch('/api/claude/agents');
      const data = await response.json();
      setAgentTemplates(data.templates || []);
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  // Load recommended MCPs
  const loadRecommendedMcps = async () => {
    try {
      const response = await fetch('/api/claude/recommended-mcps');
      const data = await response.json();
      setRecommendedMcps(data.mcps || []);
    } catch (error) {
      console.error('Failed to load recommended MCPs:', error);
    }
  };

  // Spawn agent
  const handleSpawnAgent = async () => {
    if (!selectedTemplate || !agentPrompt.trim()) return;
    setAgentLoading(true);
    try {
      const response = await fetch('/api/claude/agents/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: selectedTemplate.id, prompt: agentPrompt }),
      });
      const data = await response.json();
      if (data.success) {
        setActionResult({ action: selectedTemplate.name, response: data.response });
      }
    } catch (error) {
      console.error('Failed to spawn agent:', error);
    } finally {
      setAgentLoading(false);
      setShowAgentModal(false);
      setAgentPrompt('');
    }
  };

  // Install recommended MCP
  const handleInstallMcp = async (name: string) => {
    try {
      const response = await fetch('/api/claude/recommended-mcps/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, scope: 'global' }),
      });
      if (response.ok) {
        loadRecommendedMcps();
        mcpApi.load();
      }
    } catch (error) {
      console.error('Failed to install MCP:', error);
    }
  };

  // Quick action handlers
  const runQuickAction = async (action: string, label: string) => {
    setActionLoading(action);
    try {
      const response = await fetch(`/api/actions/${action}`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        setActionResult({ action: label, response: data.response });
      }
    } catch (error) {
      console.error(`Failed to run ${action}:`, error);
    } finally {
      setActionLoading(null);
    }
  };

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
      <Section
        title="Agents"
        onAdd={() => setShowAgentModal(true)}
        isEmpty={agentTemplates.length === 0}
        emptyText="No agent templates"
      >
        {agentTemplates.map(template => (
          <div
            key={template.id}
            className="p-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700"
            onClick={() => {
              setSelectedTemplate(template);
              setShowAgentModal(true);
            }}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">{template.name}</div>
              <span className="text-xs px-1.5 py-0.5 bg-blue-600/20 text-blue-400 rounded">
                {template.mcps.length} MCP{template.mcps.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="text-xs text-gray-500">{template.description}</div>
          </div>
        ))}
      </Section>

      {/* Recommended MCPs */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-400">Thinking MCPs</h3>
          <button
            onClick={() => setShowRecommendedMcps(!showRecommendedMcps)}
            className="text-xs px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
          >
            {showRecommendedMcps ? 'Hide' : 'Show'}
          </button>
        </div>
        {showRecommendedMcps && (
          <div className="space-y-2">
            {recommendedMcps.map(mcp => (
              <div key={mcp.name} className="p-2 bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">{mcp.name}</div>
                  {mcp.installed ? (
                    <span className="text-xs px-1.5 py-0.5 bg-green-600/20 text-green-400 rounded">
                      Installed
                    </span>
                  ) : (
                    <button
                      onClick={() => handleInstallMcp(mcp.name)}
                      className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-500"
                    >
                      Install
                    </button>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">{mcp.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <QuickAction
            onClick={() => runQuickAction('commit', 'Commit changes')}
            label="Commit changes"
            loading={actionLoading === 'commit'}
          />
          <QuickAction
            onClick={() => runQuickAction('pr', 'Create PR')}
            label="Create PR"
            loading={actionLoading === 'pr'}
          />
          <QuickAction
            onClick={() => runQuickAction('verify', 'Quality checks')}
            label="Run quality checks"
            loading={actionLoading === 'verify'}
          />
          <QuickAction
            onClick={() => runQuickAction('retrospective', 'Extract learnings')}
            label="Extract learnings"
            loading={actionLoading === 'retrospective'}
          />
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

      {/* Spawn Agent Modal */}
      <Modal isOpen={showAgentModal} onClose={() => setShowAgentModal(false)} title={selectedTemplate?.name || 'Spawn Agent'}>
        <div className="space-y-4">
          {!selectedTemplate ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-400">Select an agent template:</p>
              {agentTemplates.map(template => (
                <button
                  key={template.id}
                  onClick={() => setSelectedTemplate(template)}
                  className="w-full text-left p-3 bg-gray-800 rounded-lg hover:bg-gray-700"
                >
                  <div className="text-sm font-medium">{template.name}</div>
                  <div className="text-xs text-gray-500">{template.description}</div>
                </button>
              ))}
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-400">{selectedTemplate.description}</p>
              <div className="text-xs text-gray-500">
                Uses: {selectedTemplate.mcps.join(', ')}
              </div>
              <FormField label="What should this agent do?">
                <textarea
                  value={agentPrompt}
                  onInput={(e) => setAgentPrompt((e.target as HTMLTextAreaElement).value)}
                  rows={4}
                  placeholder="Describe the task..."
                  className="form-input"
                />
              </FormField>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setSelectedTemplate(null);
                    setAgentPrompt('');
                  }}
                  className="flex-1 px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  Back
                </button>
                <button
                  onClick={handleSpawnAgent}
                  disabled={agentLoading || !agentPrompt.trim()}
                  className="flex-1 px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50"
                >
                  {agentLoading ? 'Running...' : 'Run Agent'}
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Action Result Modal */}
      <Modal
        isOpen={!!actionResult}
        onClose={() => setActionResult(null)}
        title={actionResult?.action || 'Result'}
      >
        {actionResult && (
          <div className="space-y-4">
            <div className="max-h-96 overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap bg-gray-800 p-3 rounded-lg">
                {actionResult.response}
              </pre>
            </div>
            <button
              onClick={() => setActionResult(null)}
              className="w-full px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        )}
      </Modal>
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

function QuickAction({ onClick, label, loading }: { onClick: () => void; label: string; loading?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full text-left px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 text-sm disabled:opacity-50 flex items-center justify-between"
    >
      <span>{label}</span>
      {loading && (
        <span className="text-xs text-blue-400 animate-pulse">Running...</span>
      )}
    </button>
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
