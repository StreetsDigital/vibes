/**
 * TaskProgressPanel - Live task progress with stages and retros
 *
 * Shows:
 * - Current task being worked on
 * - Stage indicator (🚀 Starting → 🔍 Analyzing → 📝 Planning → 💻 Implementing → 🧪 Testing → ✅ Done)
 * - Progress bar
 * - 2-sentence retro on completion
 */

import { useTaskProgress } from '../hooks/useRealtime';
import type { TaskProgress } from '../hooks/useRealtime';

interface TaskCardProps {
  task: TaskProgress;
}

function TaskCard({ task }: TaskCardProps) {
  const isComplete = task.stage === 'completed';
  const isFailed = task.stage === 'failed';

  return (
    <div className={`
      p-3 rounded-lg border transition-all duration-300
      ${isComplete ? 'bg-green-900/30 border-green-600/50' :
        isFailed ? 'bg-red-900/30 border-red-600/50' :
        'bg-gray-800 border-gray-700'}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{task.stage_emoji}</span>
          <span className="font-medium text-sm truncate max-w-[200px]">
            {task.task_name}
          </span>
        </div>
        <span className={`
          text-xs px-2 py-0.5 rounded-full
          ${isComplete ? 'bg-green-600 text-white' :
            isFailed ? 'bg-red-600 text-white' :
            'bg-blue-600/50 text-blue-200'}
        `}>
          {task.stage_display}
        </span>
      </div>

      {/* Progress bar */}
      {!isComplete && !isFailed && (
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-blue-500 transition-all duration-500 ease-out"
            style={{ width: `${task.progress_percent}%` }}
          />
        </div>
      )}

      {/* Stage message */}
      <p className="text-xs text-gray-400 mb-1">
        {task.stage_message}
      </p>

      {/* Retro (shown on completion) */}
      {task.retro && (
        <div className="mt-2 p-2 bg-green-900/20 rounded border border-green-600/30">
          <p className="text-xs text-green-300 font-medium mb-1">📋 Retro</p>
          <p className="text-xs text-gray-300">{task.retro}</p>
        </div>
      )}

      {/* Error (shown on failure) */}
      {task.error && (
        <div className="mt-2 p-2 bg-red-900/20 rounded border border-red-600/30">
          <p className="text-xs text-red-300">{task.error}</p>
        </div>
      )}

      {/* Time info */}
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>Started: {new Date(task.started_at).toLocaleTimeString()}</span>
        {isComplete && (
          <span>
            Duration: {getElapsedTime(task.started_at, task.updated_at)}
          </span>
        )}
      </div>
    </div>
  );
}

function getElapsedTime(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function TaskProgressPanel() {
  const { tasks } = useTaskProgress();

  if (tasks.length === 0) {
    return null;  // Don't show panel when no active tasks
  }

  return (
    <div className="fixed bottom-4 right-4 w-80 max-h-96 overflow-y-auto z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl p-3">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
            <span className="animate-pulse">🤖</span>
            Claude Working
          </h3>
          <span className="text-xs text-gray-500">
            {tasks.length} task{tasks.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="space-y-2">
          {tasks.map(task => (
            <TaskCard key={task.task_id} task={task} />
          ))}
        </div>
      </div>
    </div>
  );
}

// Stage timeline visualization
export function StageTimeline({ stage }: { stage: string }) {
  const stages = [
    { key: 'starting', emoji: '🚀', label: 'Start' },
    { key: 'analyzing', emoji: '🔍', label: 'Analyze' },
    { key: 'planning', emoji: '📝', label: 'Plan' },
    { key: 'implementing', emoji: '💻', label: 'Build' },
    { key: 'testing', emoji: '🧪', label: 'Test' },
    { key: 'completed', emoji: '✅', label: 'Done' }
  ];

  const currentIndex = stages.findIndex(s => s.key === stage);

  return (
    <div className="flex items-center justify-between px-2 py-1">
      {stages.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <div className={`
            flex flex-col items-center
            ${i <= currentIndex ? 'opacity-100' : 'opacity-40'}
          `}>
            <span className={`
              text-lg
              ${i === currentIndex ? 'animate-bounce' : ''}
            `}>
              {s.emoji}
            </span>
            <span className="text-xs text-gray-400 mt-0.5">{s.label}</span>
          </div>
          {i < stages.length - 1 && (
            <div className={`
              w-6 h-0.5 mx-1
              ${i < currentIndex ? 'bg-green-500' : 'bg-gray-600'}
            `} />
          )}
        </div>
      ))}
    </div>
  );
}

export default TaskProgressPanel;
