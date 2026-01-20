import type { ComponentChildren } from 'preact';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ComponentChildren;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-xl p-5 w-full max-w-md max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 p-1 -mr-1"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

interface ActionSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: ComponentChildren;
}

export function ActionSheet({ isOpen, onClose, children }: ActionSheetProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-end justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-t-2xl w-full max-w-lg p-4 safe-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-12 h-1 bg-gray-600 rounded-full mx-auto mb-4"></div>
        {children}
      </div>
    </div>
  );
}
