import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { getSupabaseClient } from '../lib/supabaseClient';

type ChecklistFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'date'
  | 'email'
  | 'tel'
  | 'checkbox';

export interface ChecklistFieldSchema {
  label: string;
  name: string;
  type: ChecklistFieldType;
  required?: boolean;
}

export interface DynamicChecklistProps {
  schema: ChecklistFieldSchema[];
  /**
   * Optional metadata stored alongside the checklist values for additional context.
   */
  metadata?: Record<string, unknown> | null;
  /**
   * Allows consumers to react to a successful submission.
   */
  onSubmitSuccess?: (logId: number | string | null) => void;
}

type FormState = Record<string, string | number | boolean>;

type SubmissionState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const getDefaultValue = (field: ChecklistFieldSchema): string | number | boolean => {
  switch (field.type) {
    case 'checkbox':
      return false;
    case 'number':
      return '';
    case 'date':
      return '';
    default:
      return '';
  }
};

const coerceValueForPayload = (
  field: ChecklistFieldSchema,
  value: string | number | boolean
): string | number | boolean => {
  if (field.type === 'number') {
    if (value === '') {
      return value;
    }

    const parsed = Number(value);
    return Number.isNaN(parsed) ? value : parsed;
  }

  if (field.type === 'checkbox') {
    return Boolean(value);
  }

  return value;
};

export const DynamicChecklist = ({ schema, metadata = null, onSubmitSuccess }: DynamicChecklistProps) => {
  const initialFormState = useMemo<FormState>(() => {
    const entries = schema.map((field) => [field.name, getDefaultValue(field)] as const);
    return Object.fromEntries(entries);
  }, [schema]);

  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [submission, setSubmission] = useState<SubmissionState>({ status: 'idle' });

  useEffect(() => {
    setFormState(initialFormState);
  }, [initialFormState]);

  const handleChange = (name: string, field: ChecklistFieldSchema) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { type, checked, value } = event.target as HTMLInputElement;
      setFormState((prev) => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }));
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmission({ status: 'submitting' });

    const payloadValues = schema.reduce<Record<string, string | number | boolean>>((acc, field) => {
      const currentValue = formState[field.name];
      acc[field.name] = coerceValueForPayload(field, currentValue);
      return acc;
    }, {});

    let supabaseClient: ReturnType<typeof getSupabaseClient>;
    try {
      supabaseClient = getSupabaseClient();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to initialise Supabase client.';
      setSubmission({ status: 'error', message });
      return;
    }

    const { data, error } = await supabaseClient
      .from('checklist_logs')
      .insert([
        {
          schema,
          values: payloadValues,
          metadata,
          submitted_at: new Date().toISOString(),
        },
      ])
      .select('id')
      .single();

    if (error) {
      setSubmission({ status: 'error', message: error.message });
      return;
    }

    setSubmission({ status: 'success', message: 'Checklist saved successfully.' });
    onSubmitSuccess?.(data?.id ?? null);
  };

  const renderInput = (field: ChecklistFieldSchema) => {
    const baseInputClasses =
      'mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500';

    if (field.type === 'textarea') {
      return (
        <textarea
          id={field.name}
          name={field.name}
          required={field.required}
          className={`${baseInputClasses} min-h-[120px]`}
          value={String(formState[field.name] ?? '')}
          onChange={handleChange(field.name, field)}
        />
      );
    }

    if (field.type === 'checkbox') {
      return (
        <input
          id={field.name}
          name={field.name}
          type="checkbox"
          checked={Boolean(formState[field.name])}
          onChange={handleChange(field.name, field)}
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
      );
    }

    return (
      <input
        id={field.name}
        name={field.name}
        type={field.type}
        required={field.required}
        className={baseInputClasses}
        value={String(formState[field.name] ?? '')}
        onChange={handleChange(field.name, field)}
      />
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {schema.map((field) => (
        <div key={field.name} className="space-y-2">
          <label htmlFor={field.name} className="block text-sm font-medium text-gray-700">
            {field.label}
            {field.required && <span className="ml-1 text-red-500">*</span>}
          </label>
          {renderInput(field)}
        </div>
      ))}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submission.status === 'submitting'}
          className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-300"
        >
          {submission.status === 'submitting' ? 'Saving…' : 'Save checklist'}
        </button>
        {submission.status === 'success' && (
          <span className="text-sm text-green-600">{submission.message}</span>
        )}
        {submission.status === 'error' && (
          <span className="text-sm text-red-600">{submission.message}</span>
        )}
      </div>
    </form>
  );
};

export default DynamicChecklist;
