import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { HTMLAttributes, ReactNode } from 'react';

const alertVariants = cva(
  'relative w-full rounded-lg border p-4 [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-inherit [&>svg~*]:pl-8',
  {
    variants: {
      variant: {
        default: 'bg-surface border-border text-ink',
        success: 'bg-success-light border-success/20 text-success-dark',
        warning: 'bg-warning-light border-warning/20 text-warning-dark',
        error: 'bg-error-light border-error/20 text-error-dark',
        info: 'bg-info-light border-info/20 text-info-dark'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
);

export interface AlertProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {
  icon?: ReactNode;
}

export const Alert = ({ className, variant, icon, children, ...props }: AlertProps) => {
  const defaultIcons = {
    success: <CheckCircle className="h-5 w-5" />,
    warning: <AlertCircle className="h-5 w-5" />,
    error: <XCircle className="h-5 w-5" />,
    info: <Info className="h-5 w-5" />,
    default: null
  };

  const iconToRender = icon !== undefined ? icon : variant ? defaultIcons[variant] : null;

  return (
    <div role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      {iconToRender}
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
};

export const AlertTitle = ({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h5 className={cn('font-semibold text-sm leading-none tracking-tight', className)} {...props} />
);

export const AlertDescription = ({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <div className={cn('text-sm opacity-90', className)} {...props} />
);
