'use client';

interface CsvDownloadButtonProps {
  filename: string;
  rows: Array<Record<string, string | number | boolean | null>>;
}

function toCsv(rows: Array<Record<string, string | number | boolean | null>>): string {
  if (!rows.length) {
    return '';
  }
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(',')];

  for (const row of rows) {
    const values = headers.map((header) => {
      const value = row[header];
      if (value === null || value === undefined) {
        return '';
      }
      const stringValue = String(value);
      if (stringValue.includes(',') || stringValue.includes('\n') || stringValue.includes('"')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    });
    lines.push(values.join(','));
  }

  return `${lines.join('\n')}\n`;
}

export function CsvDownloadButton({ filename, rows }: CsvDownloadButtonProps) {
  const disabled = rows.length === 0;

  const handleClick = () => {
    if (disabled) {
      return;
    }
    const csv = toCsv(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <button type="button" className="csv-button" onClick={handleClick} disabled={disabled}>
      <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 3v12m0 0l3.5-3.5M12 15l-3.5-3.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4.5 15.75v1.5A2.25 2.25 0 006.75 19.5h10.5A2.25 2.25 0 0019.5 17.25v-1.5" strokeLinecap="round" />
      </svg>
      Export CSV
    </button>
  );
}
