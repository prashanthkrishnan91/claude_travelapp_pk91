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
  colorClass = "bg-sky-50 text-sky-600",
}: StatCardProps) {
  return (
    <div className="card p-6 flex items-start gap-4">
      <div className={clsx("flex items-center justify-center w-11 h-11 rounded-xl shrink-0", colorClass)}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-slate-500 font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
        {trend && (
          <p
            className={clsx(
              "text-xs mt-1 font-medium",
              trendUp ? "text-emerald-600" : "text-slate-400"
            )}
          >
            {trend}
          </p>
        )}
      </div>
    </div>
  );
}
