import { ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-ds-carbon text-ds-text-tertiary mb-4 border border-ds-pen-stroke">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-ds-text">{title}</h3>
      <p className="mt-1 text-sm text-ds-text-tertiary max-w-xs">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
