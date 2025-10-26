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
import { useEffect, useMemo, useState } from 'react';

type FieldType = 'text' | 'textarea' | 'checkbox' | 'temperature' | 'number';

type FieldValue = string | number | boolean | null;

export type ChecklistField = {
  id: string;
  label: string;
  type: FieldType;
  helperText?: string;
  placeholder?: string;
  required?: boolean;
  defaultValue?: FieldValue;
};

export interface DynamicChecklistProps {
  fields: ChecklistField[];
  onChange?: (id: string, value: FieldValue) => void;
  disabled?: boolean;
}

const THERMOMETER_SERVICE: BluetoothServiceUUID = 'health_thermometer';
const TEMPERATURE_CHARACTERISTIC: BluetoothCharacteristicUUID = 'temperature_measurement';

function deriveInitialValue(field: ChecklistField): FieldValue {
  if (field.defaultValue !== undefined) {
    return field.defaultValue;
  }
  if (field.type === 'checkbox') {
    return false;
  }
  if (field.type === 'temperature' || field.type === 'number') {
    return null;
  }
  return '';
}

function parseTemperatureMeasurement(data: DataView): number | null {
  if (data.byteLength < 5) {
    return null;
  }
  const value = data.getFloat32(1, /* littleEndian */ true);
  if (Number.isNaN(value) || !Number.isFinite(value)) {
    return null;
  }
  return Math.round(value * 10) / 10;
}

async function readThermometerValue(device: BluetoothDevice): Promise<number | null> {
  if (!device.gatt) {
    return null;
  }

  let server: BluetoothRemoteGATTServer | null = null;
  try {
    server = await device.gatt.connect();
    const service = await server.getPrimaryService(THERMOMETER_SERVICE);
    const characteristic = await service.getCharacteristic(TEMPERATURE_CHARACTERISTIC);
    const data = await characteristic.readValue();
    return parseTemperatureMeasurement(data);
  } finally {
    if (server?.connected) {
      try {
        server.disconnect();
      } catch (error) {
        console.warn('Unable to disconnect from thermometer device', error);
      }
    }
  }
}

async function findThermoDevice(): Promise<BluetoothDevice | null> {
  const bluetooth = navigator.bluetooth;
  if (!bluetooth?.requestDevice) {
    return null;
  }

  const requestOptions: RequestDeviceOptions = {
    filters: [{ namePrefix: 'Thermo' }],
    optionalServices: [THERMOMETER_SERVICE],
  };

  try {
    const device = await bluetooth.requestDevice(requestOptions);
    return device;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'NotFoundError') {
      try {
        const device = await bluetooth.requestDevice({
          acceptAllDevices: true,
          optionalServices: [THERMOMETER_SERVICE],
        });
        if (device.name?.toLowerCase().includes('thermo')) {
          return device;
        }
      } catch (fallbackError) {
        console.warn('Fallback BLE scan failed', fallbackError);
        return null;
      }
    } else {
      console.warn('BLE scan failed', error);
    }
  }

  return null;
}

export function DynamicChecklist({ fields, onChange, disabled = false }: DynamicChecklistProps) {
  const [values, setValues] = useState<Record<string, FieldValue>>(() => {
    const initial: Record<string, FieldValue> = {};
    for (const field of fields) {
      initial[field.id] = deriveInitialValue(field);
    }
    return initial;
  });

  useEffect(() => {
    setValues((prev) => {
      const next = { ...prev };
      for (const field of fields) {
        if (!(field.id in next)) {
          next[field.id] = deriveInitialValue(field);
        }
      }
      for (const key of Object.keys(next)) {
        if (!fields.some((field) => field.id === key)) {
          delete next[key];
        }
      }
      return next;
    });
  }, [fields]);

  const temperatureField = useMemo(
    () => fields.find((field) => field.type === 'temperature'),
    [fields],
  );

  useEffect(() => {
    if (!temperatureField) {
      return;
    }
    const currentValue = values[temperatureField.id];
    if (currentValue !== null && currentValue !== undefined && currentValue !== '') {
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.bluetooth) {
      return;
    }

    let cancelled = false;

    const scanAndPopulate = async () => {
      try {
        const device = await findThermoDevice();
        if (!device || !device.name?.toLowerCase().includes('thermo')) {
          return;
        }
        const temperature = await readThermometerValue(device);
        if (temperature === null || cancelled) {
          return;
        }
        setValues((prev) => {
          if (prev[temperatureField.id] === temperature) {
            return prev;
          }
          return { ...prev, [temperatureField.id]: temperature };
        });
        onChange?.(temperatureField.id, temperature);
      } catch (error) {
        console.warn('Unable to populate temperature from BLE', error);
      }
    };

    scanAndPopulate();

    return () => {
      cancelled = true;
    };
  }, [onChange, temperatureField, values]);

  const handleFieldChange = (field: ChecklistField, value: FieldValue) => {
    setValues((prev) => {
      if (prev[field.id] === value) {
        return prev;
      }
      return { ...prev, [field.id]: value };
    });
    onChange?.(field.id, value);
  };

  const renderField = (field: ChecklistField) => {
    const value = values[field.id];
    const commonProps = {
      id: field.id,
      name: field.id,
      disabled,
      required: field.required,
      'aria-describedby': field.helperText ? `${field.id}-helper` : undefined,
    } as const;

    switch (field.type) {
      case 'checkbox':
        return (
          <div key={field.id} className="flex items-center gap-2">
            <input
              {...commonProps}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(event) => handleFieldChange(field, event.target.checked)}
            />
            <label htmlFor={field.id} className="text-sm font-medium text-slate-700">
              {field.label}
            </label>
            {field.helperText && (
              <p id={`${field.id}-helper`} className="text-xs text-slate-500">
                {field.helperText}
              </p>
            )}
          </div>
        );
      case 'textarea':
        return (
          <div key={field.id} className="flex flex-col gap-1">
            <label htmlFor={field.id} className="text-sm font-medium text-slate-700">
              {field.label}
            </label>
            <textarea
              {...commonProps}
              placeholder={field.placeholder}
              value={(value ?? '') as string}
              onChange={(event) => handleFieldChange(field, event.target.value)}
              className="rounded border border-slate-300 p-2 text-sm"
              rows={3}
            />
            {field.helperText && (
              <p id={`${field.id}-helper`} className="text-xs text-slate-500">
                {field.helperText}
              </p>
            )}
          </div>
        );
      case 'temperature':
      case 'number':
        return (
          <div key={field.id} className="flex flex-col gap-1">
            <label htmlFor={field.id} className="text-sm font-medium text-slate-700">
              {field.label}
            </label>
            <input
              {...commonProps}
              type="number"
              inputMode="decimal"
              step="0.1"
              placeholder={field.placeholder}
              value={value ?? ''}
              onChange={(event) => {
                const raw = event.target.value;
                handleFieldChange(field, raw === '' ? null : Number(raw));
              }}
              className="rounded border border-slate-300 p-2 text-sm"
            />
            {field.helperText && (
              <p id={`${field.id}-helper`} className="text-xs text-slate-500">
                {field.helperText}
              </p>
            )}
          </div>
        );
      default:
        return (
          <div key={field.id} className="flex flex-col gap-1">
            <label htmlFor={field.id} className="text-sm font-medium text-slate-700">
              {field.label}
            </label>
            <input
              {...commonProps}
              type="text"
              placeholder={field.placeholder}
              value={(value ?? '') as string}
              onChange={(event) => handleFieldChange(field, event.target.value)}
              className="rounded border border-slate-300 p-2 text-sm"
            />
            {field.helperText && (
              <p id={`${field.id}-helper`} className="text-xs text-slate-500">
                {field.helperText}
              </p>
            )}
          </div>
        );
    }
  };

  return <div className="space-y-4">{fields.map(renderField)}</div>;
}

export default DynamicChecklist;
