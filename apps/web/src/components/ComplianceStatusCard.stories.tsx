import type { ComplianceStatusCardProps } from './ComplianceStatusCard';
import { ComplianceStatusCard } from './ComplianceStatusCard';

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
    {
      id: 'health-permit',
      name: 'Health Permit',
      tone: 'warning',
      label: 'Expiring soon',
      message: 'Schedule renewal inspection at least 30 days prior to expiration.',
      issuedBy: 'County Health Department',
      referenceId: 'HP-7781',
      expiresOn: 'Aug 15, 2024',
    },
  ],
  pdfEndpoint: '/api/compliance/packets/harborview.pdf',
};

export default {
  title: 'Compliance/ComplianceStatusCard',
  component: ComplianceStatusCard,
  tags: ['autodocs'],
};

export const Default = {
  args: baseProps,
};

export const ExpiringSoon = {
  args: {
    ...baseProps,
    sublease: {
      ...baseProps.sublease,
      tone: 'warning',
      label: 'Renewal needed',
      message: 'Lease renewal pending signature from landlord partner.',
      expiresOn: 'Jun 30, 2024',
      renewalDate: 'Jun 15, 2024',
    },
    certificateOfInsurance: {
      ...baseProps.certificateOfInsurance,
      tone: 'warning',
      label: 'COI expires soon',
      message: 'Request updated certificate from broker before coverage lapses.',
      expiresOn: 'Jul 01, 2024',
    },
  },
};

export const MissingDocuments = {
  args: {
    ...baseProps,
    permits: [],
    sublease: {
      ...baseProps.sublease,
      tone: 'critical',
      label: 'Sublease missing',
      message: 'No active sublease on file. Upload signed agreement to continue operations.',
      expiresOn: undefined,
      renewalDate: undefined,
    },
    certificateOfInsurance: {
      ...baseProps.certificateOfInsurance,
      tone: 'critical',
      label: 'COI missing',
      message: 'Upload a current certificate of insurance with required coverage limits.',
      expiresOn: undefined,
    },
  },
};
