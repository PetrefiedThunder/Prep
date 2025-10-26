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
