export const formatCurrency = (value: number, currency = 'USD', locale = 'en-US') =>
  new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0
  }).format(value);
