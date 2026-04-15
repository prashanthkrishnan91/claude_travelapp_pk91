import clsx from "clsx";
import type { TripStatus } from "@/types";

const MAP: Record<TripStatus, { label: string; cls: string; dotCls: string }> = {
  draft:       { label: "Draft",       cls: "badge-draft",     dotCls: "dot-draft"       },
  researching: { label: "Researching", cls: "badge-active",    dotCls: "dot-researching" },
  planned:     { label: "Planned",     cls: "badge-planned",   dotCls: "dot-planned"     },
  booked:      { label: "Booked",      cls: "badge-booked",    dotCls: "dot-booked"      },
  completed:   { label: "Completed",   cls: "badge-completed", dotCls: "dot-completed"   },
  archived:    { label: "Archived",    cls: "badge-archived",  dotCls: "dot-archived"    },
};

export function TripStatusBadge({ status }: { status: TripStatus }) {
  const { label, cls, dotCls } = MAP[status] ?? MAP.draft;
  return (
    <span className={clsx("badge", cls)}>
      <span className={clsx("status-dot", dotCls)} />
      {label}
    </span>
  );
}
