import { ReactNode } from 'react';

interface DataSectionProps {
  title: string;
  description?: string;
  controls?: ReactNode;
  children: ReactNode;
}

export function DataSection({ title, description, controls, children }: DataSectionProps) {
  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">{title}</h2>
          {description ? <p className="section-description">{description}</p> : null}
        </div>
        {controls}
      </div>
      {children}
    </section>
  );
}
