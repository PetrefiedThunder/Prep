'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo } from 'react';

const NAV_ITEMS = [
  { href: '/', label: 'Overview' },
  { href: '/policy-decisions', label: 'Policy decisions' },
  { href: '/fees', label: 'Fee schedules' },
  { href: '/documents', label: 'Documents' }
];

export function Navigation() {
  const pathname = usePathname();

  const items = useMemo(() => {
    return NAV_ITEMS.map((item) => {
      const isActive = pathname === item.href;
      return { ...item, isActive };
    });
  }, [pathname]);

  return (
    <header
      style={{
        background: 'var(--surface-contrast)',
        borderBottom: '1px solid var(--border-color)',
        position: 'sticky',
        top: 0,
        zIndex: 40
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem 2rem',
          gap: '1.5rem'
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <Link href="/" style={{ fontWeight: 700, fontSize: '1.1rem' }}>
            Prep City Console
          </Link>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
            Operational telemetry for compliance teams
          </span>
        </div>
        <nav style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: '0.45rem 0.9rem',
                borderRadius: '9999px',
                fontSize: '0.95rem',
                fontWeight: 600,
                background: item.isActive ? 'rgba(37, 99, 235, 0.12)' : 'transparent',
                color: item.isActive ? 'var(--accent)' : 'var(--muted-foreground)',
                border: item.isActive ? '1px solid rgba(37, 99, 235, 0.3)' : '1px solid transparent'
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
