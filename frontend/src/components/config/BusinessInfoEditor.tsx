import { useState } from 'react';
import { Save } from 'lucide-react';
import type { ConfigValue } from '../../types/config';

interface BusinessInfoEditorProps {
  data: ConfigValue;
  onSave: (value: ConfigValue) => void;
  isSaving: boolean;
}

export function BusinessInfoEditor({ data, onSave, isSaving }: BusinessInfoEditorProps) {
  const [value, setValue] = useState(JSON.stringify(data, null, 2));
  const [parseError, setParseError] = useState('');

  const handleSave = () => {
    try {
      const parsed = JSON.parse(value);
      setParseError('');
      onSave(parsed);
    } catch {
      setParseError('Invalid JSON format');
    }
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Business Info</h3>
      <textarea
        className="input-field font-mono text-xs"
        rows={10}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-label="Business info JSON"
      />
      {parseError && <p className="mt-1 text-sm text-red-600">{parseError}</p>}
      <div className="mt-3 flex justify-end">
        <button onClick={handleSave} disabled={isSaving} className="btn-primary text-sm flex items-center gap-1">
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving...' : 'Save Business Info'}
        </button>
      </div>
    </div>
  );
}
