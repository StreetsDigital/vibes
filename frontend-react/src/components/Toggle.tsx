interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Toggle({ checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange((e.target as HTMLInputElement).checked)}
        disabled={disabled}
        className="sr-only peer"
      />
      <div className="w-9 h-5 bg-gray-600 peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
    </label>
  );
}
