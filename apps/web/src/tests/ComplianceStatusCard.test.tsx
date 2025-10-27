import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  ComplianceStatusCard,
  type ComplianceStatusCardProps,
} from '../components/ComplianceStatusCard';

describe('ComplianceStatusCard', () => {
  const baseProps: ComplianceStatusCardProps = {
    kitchenName: 'Harborview Test Kitchen',
    sublease: {
      tone: 'good',
      label: 'Active sublease',
      message: 'Agreement confirmed and payments current through the end of the term.',
      expiresOn: 'Dec 31, 2024',
      lastUpdated: 'May 28, 2024',
      renewalDate: 'Nov 30, 2024',
    },
    certificateOfInsurance: {
      tone: 'good',
      label: 'Valid COI on file',
      message: 'Coverage meets Prep minimum requirements for general liability.',
      expiresOn: 'Jan 31, 2025',
      lastUpdated: 'Apr 02, 2024',
      coverageLimit: '$2M aggregate / $1M per occurrence',
      broker: 'Acme Insurance Brokerage',
    },
    permits: [
      {
        id: 'business-license',
        name: 'Business License',
        tone: 'good',
        label: 'Active',
        message: 'License renewed with the city and valid for the current fiscal year.',
        issuedBy: 'City of Harborview',
        referenceId: 'BL-2048-22',
        expiresOn: 'Jun 30, 2025',
      },
    ],
    pdfEndpoint: '/api/compliance/packets/harborview.pdf',
  };

  const originalFetch = global.fetch;
  const originalCreateObjectURL = global.URL.createObjectURL;
  const originalRevokeObjectURL = global.URL.revokeObjectURL;

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
    global.URL.createObjectURL = originalCreateObjectURL;
    global.URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it('renders sublease, COI, and permit information', () => {
    render(<ComplianceStatusCard {...baseProps} />);

    expect(screen.getByText(/Compliance summary/i)).toBeInTheDocument();
    expect(screen.getByText('Harborview Test Kitchen compliance')).toBeInTheDocument();
    expect(screen.getByText('Sublease status')).toBeInTheDocument();
    expect(screen.getByText('Active sublease')).toBeInTheDocument();
    expect(screen.getByText('Certificate of Insurance')).toBeInTheDocument();
    expect(screen.getByText('Valid COI on file')).toBeInTheDocument();
    expect(screen.getByText('Business License')).toBeInTheDocument();
  });

  it('downloads the compliance packet when the button is clicked', async () => {
    const user = userEvent.setup();
    const blobResponse = new Response('pdf-data', {
      status: 200,
      headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="test.pdf"' },
    });
    const fetchMock = vi.fn().mockResolvedValue(blobResponse);
    global.fetch = fetchMock as unknown as typeof global.fetch;

    const createObjectURLMock = vi.fn().mockReturnValue('blob:compliance-packet');
    const revokeObjectURLMock = vi.fn();
    global.URL.createObjectURL = createObjectURLMock;
    global.URL.revokeObjectURL = revokeObjectURLMock;

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(<ComplianceStatusCard {...baseProps} pdfFileName="custom.pdf" />);

    await user.click(screen.getByRole('button', { name: /download compliance packet/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/compliance/packets/harborview.pdf', { method: 'GET' });
      expect(createObjectURLMock).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
    });

    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:compliance-packet');
    expect(screen.getByText(/Compliance packet downloaded/i)).toBeInTheDocument();
  });

  it('shows an error message when the download fails', async () => {
    const user = userEvent.setup();
    const error = new Error('Network error');
    const fetchMock = vi.fn().mockRejectedValue(error);
    global.fetch = fetchMock as unknown as typeof global.fetch;

    const onDownloadError = vi.fn();

    render(<ComplianceStatusCard {...baseProps} onDownloadError={onDownloadError} />);

    await user.click(screen.getByRole('button', { name: /download compliance packet/i }));

    await waitFor(() => {
      expect(onDownloadError).toHaveBeenCalledWith('Network error');
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
