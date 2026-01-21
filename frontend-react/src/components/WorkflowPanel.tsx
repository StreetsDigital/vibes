import { useState, useEffect, useRef } from 'preact/hooks';

interface WorkflowStage {
  id: number;
  name: string;
  shortName: string;
  keywords: string[];
  description: string;
}

const WORKFLOW_STAGES: WorkflowStage[] = [
  {
    id: 1,
    name: 'GET NEXT FEATURE',
    shortName: 'Feature',
    keywords: ['feature_get_next', 'next feature', 'getting feature', 'feature queue'],
    description: 'Fetching next task from queue'
  },
  {
    id: 2,
    name: 'PRE-PLANNING',
    shortName: 'Planning',
    keywords: ['skill-discovery', 'feature_discuss', 'feature_assumptions', 'feature_research', 'add-skill', 'npx skills'],
    description: 'Discovering skills & clarifying requirements'
  },
  {
    id: 3,
    name: 'REFRESH CONTEXT',
    shortName: 'Context',
    keywords: ['task_plan.md', 'findings.md', 'progress.md', 'planning-with-files', 'Read task_plan'],
    description: 'Loading planning files'
  },
  {
    id: 4,
    name: 'EXPLORE CODEBASE',
    shortName: 'Explore',
    keywords: ['aleph_search', 'aleph_peek', 'aleph_cite', 'Grep', 'Glob', 'searching', 'exploring'],
    description: 'Searching and understanding code'
  },
  {
    id: 5,
    name: 'IMPLEMENT',
    shortName: 'Implement',
    keywords: ['Write', 'Edit', 'writing code', 'implementing', 'creating file', 'editing file'],
    description: 'Writing code and tests'
  },
  {
    id: 6,
    name: 'QUALITY CHECK',
    shortName: 'Quality',
    keywords: ['quality_check', 'feature_verify', 'npm test', 'pytest', 'lint', 'tsc', 'type check', 'running tests'],
    description: 'Running verification suite'
  },
  {
    id: 7,
    name: 'MARK COMPLETE',
    shortName: 'Complete',
    keywords: ['feature_mark_passing', 'aleph_refresh', 'marking complete', 'task complete'],
    description: 'Finalizing and committing'
  },
  {
    id: 8,
    name: 'COMMIT',
    shortName: 'Commit',
    keywords: ['/commit', 'git commit', 'git add', 'committing', 'committed'],
    description: 'Committing changes'
  },
  {
    id: 9,
    name: 'LEARN',
    shortName: 'Learn',
    keywords: ['/retrospective', 'extract learnings', 'saving skill', 'knowledge extraction'],
    description: 'Extracting reusable knowledge'
  }
];

interface WorkflowEvent {
  timestamp: string;
  stage: number;
  message: string;
}

export function WorkflowPanel() {
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [isPolling, setIsPolling] = useState(true);
  const [lastActivity, setLastActivity] = useState<string>('');
  const pollRef = useRef<number | null>(null);
  const seenMessagesRef = useRef<Set<string>>(new Set());

  const detectStage = (message: string): number | null => {
    const lowerMsg = message.toLowerCase();
    for (const stage of WORKFLOW_STAGES) {
      for (const keyword of stage.keywords) {
        if (lowerMsg.includes(keyword.toLowerCase())) {
          return stage.id;
        }
      }
    }
    return null;
  };

  const fetchAndAnalyzeLogs = async () => {
    try {
      const response = await fetch('/api/logs?filter=all&limit=50');
      const data = await response.json();
      const logs = data.logs || [];

      for (const log of logs.reverse()) {
        const msgKey = `${log.timestamp}-${log.message}`;
        if (seenMessagesRef.current.has(msgKey)) continue;
        seenMessagesRef.current.add(msgKey);

        const detectedStage = detectStage(log.message);
        if (detectedStage && detectedStage !== currentStage) {
          setCurrentStage(detectedStage);
          setLastActivity(log.message);
          setEvents(prev => [{
            timestamp: log.timestamp,
            stage: detectedStage,
            message: log.message.slice(0, 100)
          }, ...prev].slice(0, 20));
        }
      }
    } catch (e) {
      console.error('Failed to fetch workflow logs:', e);
    }
  };

  useEffect(() => {
    fetchAndAnalyzeLogs();
    if (isPolling) {
      pollRef.current = window.setInterval(fetchAndAnalyzeLogs, 2000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isPolling]);

  const getStageStatus = (stageId: number): 'completed' | 'current' | 'pending' => {
    if (stageId < currentStage) return 'completed';
    if (stageId === currentStage) return 'current';
    return 'pending';
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-gray-300">Workflow Pipeline</h2>
          <p className="text-xs text-gray-500">Production-ready loop status</p>
        </div>
        <button
          onClick={() => setIsPolling(!isPolling)}
          className={`px-3 py-1 text-xs rounded-full flex items-center gap-2 ${
            isPolling
              ? 'bg-green-600/30 text-green-400 border border-green-500/50'
              : 'bg-gray-700 text-gray-400'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${isPolling ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
          {isPolling ? 'Live' : 'Paused'}
        </button>
      </div>

      {/* Pipeline Visualization */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2">
          {WORKFLOW_STAGES.map((stage, idx) => {
            const status = getStageStatus(stage.id);
            return (
              <div key={stage.id} className="flex items-center">
                <div
                  className={`flex flex-col items-center min-w-[60px] ${
                    status === 'current' ? 'scale-110' : ''
                  }`}
                  title={`${stage.name}: ${stage.description}`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      status === 'completed'
                        ? 'bg-green-600 text-white'
                        : status === 'current'
                        ? 'bg-blue-500 text-white ring-2 ring-blue-400 ring-offset-2 ring-offset-gray-900 animate-pulse'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {status === 'completed' ? '✓' : stage.id}
                  </div>
                  <span
                    className={`text-[10px] mt-1 text-center ${
                      status === 'current' ? 'text-blue-400 font-medium' : 'text-gray-500'
                    }`}
                  >
                    {stage.shortName}
                  </span>
                </div>
                {idx < WORKFLOW_STAGES.length - 1 && (
                  <div
                    className={`w-4 h-0.5 mx-0.5 ${
                      status === 'completed' ? 'bg-green-600' : 'bg-gray-700'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Stage Detail */}
      {currentStage > 0 && (
        <div className="p-4 border-b border-gray-700 bg-blue-900/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-lg font-bold">
              {currentStage}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-blue-400">
                {WORKFLOW_STAGES[currentStage - 1]?.name}
              </div>
              <div className="text-xs text-gray-400 truncate">
                {lastActivity || WORKFLOW_STAGES[currentStage - 1]?.description}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Event Log */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-xs font-medium text-gray-400 mb-3">Stage Transitions</h3>
        {events.length === 0 ? (
          <div className="text-sm text-gray-500 text-center py-8">
            <div className="text-2xl mb-2">🔄</div>
            Waiting for workflow activity...
            <div className="text-xs mt-2">Send a message to Claude to see the pipeline in action</div>
          </div>
        ) : (
          <div className="space-y-2">
            {events.map((event, idx) => (
              <div
                key={idx}
                className="p-2 bg-gray-800 rounded-lg text-xs"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    event.stage <= 3 ? 'bg-purple-600/30 text-purple-400' :
                    event.stage <= 6 ? 'bg-blue-600/30 text-blue-400' :
                    'bg-green-600/30 text-green-400'
                  }`}>
                    {WORKFLOW_STAGES[event.stage - 1]?.shortName}
                  </span>
                  <span className="text-gray-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-gray-300 truncate">{event.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="p-3 border-t border-gray-700 bg-gray-800/50">
        <div className="flex items-center justify-center gap-4 text-[10px] text-gray-500">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-green-600" />
            <span>Completed</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
            <span>Current</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-gray-700" />
            <span>Pending</span>
          </div>
        </div>
      </div>
    </div>
  );
}
