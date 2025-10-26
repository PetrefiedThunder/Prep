import { render, screen, waitFor } from '@testing-library/react';
import DynamicChecklist from '../components/DynamicChecklist';

describe('DynamicChecklist temperature integration', () => {
  const originalBluetooth = navigator.bluetooth;

  afterEach(() => {
    if (originalBluetooth) {
      Object.defineProperty(navigator, 'bluetooth', {
        value: originalBluetooth,
        configurable: true,
        writable: true,
      });
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (navigator as any).bluetooth;
    }
  });

  it('auto-fills temperature fields using the first Thermo BLE device', async () => {
    const buffer = new ArrayBuffer(5);
    const view = new DataView(buffer);
    view.setUint8(0, 0);
    view.setFloat32(1, 21.5, true);

    const readValue = vi.fn().mockResolvedValue(view);
    const getCharacteristic = vi.fn().mockResolvedValue({ readValue });
    const getPrimaryService = vi.fn().mockResolvedValue({ getCharacteristic });
    const disconnect = vi.fn();
    const connect = vi.fn().mockResolvedValue({ getPrimaryService, disconnect, connected: true });

    const requestDevice = vi.fn().mockResolvedValue({
      name: 'ThermoTrack 01',
      gatt: { connect },
    });

    Object.defineProperty(navigator, 'bluetooth', {
      value: { requestDevice },
      configurable: true,
      writable: true,
    });

    const handleChange = vi.fn();

    render(
      <DynamicChecklist
        fields={[{ id: 'temp', label: 'Food temperature', type: 'temperature' }]}
        onChange={handleChange}
      />,
    );

    await waitFor(() => expect(requestDevice).toHaveBeenCalled());

    const input = await screen.findByLabelText('Food temperature');

    await waitFor(() => {
      expect(handleChange).toHaveBeenCalledWith('temp', 21.5);
      expect(input).toHaveValue(21.5);
    });

    expect(connect).toHaveBeenCalled();
    expect(getPrimaryService).toHaveBeenCalledWith('health_thermometer');
    expect(getCharacteristic).toHaveBeenCalledWith('temperature_measurement');
    expect(readValue).toHaveBeenCalled();
    expect(disconnect).toHaveBeenCalled();
  });
});
