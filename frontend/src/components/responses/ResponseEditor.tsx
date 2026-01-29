import { useForm } from 'react-hook-form';
import { X, Save } from 'lucide-react';

interface ResponseEditorProps {
  initialContent: string;
  onSave: (content: string) => void;
  onCancel: () => void;
  isSaving?: boolean;
}

interface FormData {
  content: string;
}

export function ResponseEditor({ initialContent, onSave, onCancel, isSaving }: ResponseEditorProps) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    defaultValues: { content: initialContent },
  });

  const onSubmit = (data: FormData) => {
    onSave(data.content);
  };

  return (
    <div className="card p-4">
      <form onSubmit={handleSubmit(onSubmit)}>
        <label htmlFor="response-content" className="block text-sm font-medium text-gray-700 mb-2">
          Edit Response Content
        </label>
        <textarea
          id="response-content"
          rows={10}
          className={`input-field font-mono text-sm ${errors.content ? 'input-error' : ''}`}
          {...register('content', {
            required: 'Response content is required',
            maxLength: { value: 50000, message: 'Content must be 50,000 characters or fewer' },
          })}
        />
        {errors.content && (
          <p className="mt-1 text-sm text-red-600" role="alert">{errors.content.message}</p>
        )}
        <div className="flex justify-end gap-3 mt-4">
          <button type="button" onClick={onCancel} className="btn-secondary text-sm flex items-center gap-1">
            <X className="w-4 h-4" />
            Cancel
          </button>
          <button type="submit" disabled={isSaving} className="btn-primary text-sm flex items-center gap-1">
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}
