import type { Task } from '../types';

interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onDragStart: (e: DragEvent, taskId: string) => void;
}

export function TaskCard({ task, onClick, onDragStart }: TaskCardProps) {
  return (
    <div
      className="bg-gray-700 rounded-lg p-3 cursor-pointer hover:bg-gray-600 active:bg-gray-500 transition-colors touch-manipulation"
      draggable
      onDragStart={(e) => onDragStart(e as unknown as DragEvent, task.id)}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium text-sm">{task.name}</span>
        {task.priority > 50 && (
          <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">
            High
          </span>
        )}
      </div>
      {task.description && (
        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
          {task.description}
        </p>
      )}
      {task.test_cases && task.test_cases.length > 0 && (
        <div className="text-xs text-gray-500 mt-2">
          {task.test_cases.length} tests
        </div>
      )}
    </div>
  );
}
