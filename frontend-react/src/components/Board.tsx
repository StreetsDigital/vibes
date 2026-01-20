import { useState } from 'preact/hooks';
import type { Task, BoardData } from '../types';
import { TaskCard } from './TaskCard';
import { Modal } from './Modal';

interface BoardProps {
  data: BoardData | null;
  onMoveTask: (taskId: string, status: string) => void;
  onAddTask: (task: Partial<Task>) => void;
  onWorkOnTask: (task: Task) => void;
}

const columns = [
  { id: 'pending', key: 'todo', label: 'To Do', color: 'bg-gray-500' },
  { id: 'in_progress', key: 'in_progress', label: 'In Progress', color: 'bg-blue-500' },
  { id: 'needs_review', key: 'review', label: 'Review', color: 'bg-yellow-500' },
  { id: 'passing', key: 'done', label: 'Done', color: 'bg-green-500' },
];

export function Board({ data, onMoveTask, onAddTask, onWorkOnTask }: BoardProps) {
  const [showAddTask, setShowAddTask] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [newTask, setNewTask] = useState({ name: '', description: '', testCases: '' });
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  const handleDragStart = (e: DragEvent, taskId: string) => {
    e.dataTransfer?.setData('taskId', taskId);
  };

  const handleDragOver = (e: DragEvent, columnId: string) => {
    e.preventDefault();
    setDragOverColumn(columnId);
  };

  const handleDrop = (e: DragEvent, status: string) => {
    e.preventDefault();
    setDragOverColumn(null);
    const taskId = e.dataTransfer?.getData('taskId');
    if (taskId) {
      onMoveTask(taskId, status);
    }
  };

  const handleAddTask = (e: Event) => {
    e.preventDefault();
    onAddTask({
      name: newTask.name,
      description: newTask.description,
      test_cases: newTask.testCases.split('\n').filter(t => t.trim()),
      priority: 0,
    });
    setNewTask({ name: '', description: '', testCases: '' });
    setShowAddTask(false);
  };

  const getColumnTasks = (key: string): Task[] => {
    if (!data?.board) return [];
    return (data.board as Record<string, Task[]>)[key] || [];
  };

  const getColumnCount = (key: string): number => {
    return getColumnTasks(key).length;
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Kanban Columns */}
      <div className="flex-1 overflow-x-auto overflow-y-auto kanban-scroll p-4">
        <div className="flex md:grid md:grid-cols-4 gap-3 min-w-max md:min-w-0">
          {columns.map((col) => (
            <div
              key={col.id}
              className={`w-72 md:w-auto bg-gray-800 rounded-lg p-3 flex-shrink-0 ${
                dragOverColumn === col.id ? 'ring-2 ring-blue-500' : ''
              }`}
              onDragOver={(e) => handleDragOver(e as unknown as DragEvent, col.id)}
              onDragLeave={() => setDragOverColumn(null)}
              onDrop={(e) => handleDrop(e as unknown as DragEvent, col.id)}
            >
              <h2 className="font-semibold text-gray-300 mb-3 flex items-center gap-2 text-sm">
                <span className={`w-2.5 h-2.5 ${col.color} rounded-full`}></span>
                {col.label}
                <span className="text-xs bg-gray-700 px-2 py-0.5 rounded-full">
                  {getColumnCount(col.key)}
                </span>
              </h2>
              <div className="space-y-2 min-h-[150px]">
                {getColumnTasks(col.key).map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onClick={() => setSelectedTask(task)}
                    onDragStart={handleDragStart}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Task Button */}
      <div className="p-4 border-t border-gray-700 flex-shrink-0 safe-bottom">
        <button
          onClick={() => setShowAddTask(true)}
          className="w-full md:w-auto px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500 active:bg-blue-700 text-sm font-medium"
        >
          + Add Task
        </button>
      </div>

      {/* Add Task Modal */}
      <Modal isOpen={showAddTask} onClose={() => setShowAddTask(false)} title="Add New Task">
        <form onSubmit={handleAddTask}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input
                type="text"
                value={newTask.name}
                onInput={(e) => setNewTask({ ...newTask, name: (e.target as HTMLInputElement).value })}
                required
                className="w-full bg-gray-700 rounded-lg px-3 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Description</label>
              <textarea
                value={newTask.description}
                onInput={(e) => setNewTask({ ...newTask, description: (e.target as HTMLTextAreaElement).value })}
                rows={3}
                className="w-full bg-gray-700 rounded-lg px-3 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Test Cases (one per line)</label>
              <textarea
                value={newTask.testCases}
                onInput={(e) => setNewTask({ ...newTask, testCases: (e.target as HTMLTextAreaElement).value })}
                rows={3}
                placeholder="Test case 1&#10;Test case 2"
                className="w-full bg-gray-700 rounded-lg px-3 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-6">
            <button
              type="button"
              onClick={() => setShowAddTask(false)}
              className="flex-1 px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500"
            >
              Add
            </button>
          </div>
        </form>
      </Modal>

      {/* Task Detail Modal */}
      <Modal
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        title={selectedTask?.name || ''}
      >
        {selectedTask && (
          <>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500">Status</label>
                <p className="text-sm">{selectedTask.status}</p>
              </div>
              {selectedTask.description && (
                <div>
                  <label className="text-xs text-gray-500">Description</label>
                  <p className="text-sm">{selectedTask.description}</p>
                </div>
              )}
              {selectedTask.test_cases && selectedTask.test_cases.length > 0 && (
                <div>
                  <label className="text-xs text-gray-500">Test Cases</label>
                  <ul className="text-sm list-disc list-inside">
                    {selectedTask.test_cases.map((tc, i) => (
                      <li key={i}>{tc}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setSelectedTask(null)}
                className="flex-1 px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600"
              >
                Close
              </button>
              <button
                onClick={() => {
                  onWorkOnTask(selectedTask);
                  setSelectedTask(null);
                }}
                className="flex-1 px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500"
              >
                Work on this
              </button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
