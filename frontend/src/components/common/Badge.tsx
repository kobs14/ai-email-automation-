import { clsx } from 'clsx';

type BadgeVariant = 'pending' | 'classified' | 'approved' | 'sent' | 'responded' | 'rejected' | 'failed' | 'draft' | 'default';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  draft: 'bg-yellow-100 text-yellow-800',
  classified: 'bg-blue-100 text-blue-800',
  approved: 'bg-indigo-100 text-indigo-800',
  sent: 'bg-green-100 text-green-800',
  responded: 'bg-green-100 text-green-800',
  rejected: 'bg-gray-100 text-gray-800',
  failed: 'bg-red-100 text-red-800',
  default: 'bg-gray-100 text-gray-700',
};

export function Badge({ variant = 'default', children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const variant = (status in variantClasses ? status : 'default') as BadgeVariant;
  return <Badge variant={variant}>{status}</Badge>;
}
