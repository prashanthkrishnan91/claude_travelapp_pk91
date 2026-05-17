import { ReactNode } from "react";
import clsx from "clsx";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  trend?: string;
  trendUp?: boolean;
  colorClass?: string;
}

export function StatCard({
  label,
  value,
  icon,
  trend,
  trendUp,
  colorClass = "text-ds-accent",
}: StatCardProps) {
  return (
    <div className="card p-6 flex items-start gap-4">
      <div className={clsx("flex items-center justify-center w-11 h-11 rounded-xl shrink-0", colorClass)}
        style={{ backgroundColor: "var(--ds-accent-subtle)" }}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-ds-text-tertiary font-medium">{label}</p>
        <p className="text-2xl font-bold text-ds-text mt-0.5">{value}</p>
        {trend && (
          <p
            className={clsx(
              "text-xs mt-1 font-medium",
              trendUp ? "text-ds-trust" : "text-ds-text-tertiary"
            )}
          >
            {trend}
          </p>
        )}
      </div>
    </div>
  );
}
