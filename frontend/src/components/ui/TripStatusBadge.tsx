import clsx from "clsx";
import type { TripStatus } from "@/types";

const MAP: Record<TripStatus, { label: string; cls: string }> = {
  draft:       { label: "Draft",       cls: "badge-draft"    },
  researching: { label: "Researching", cls: "badge-active"   },
  planned:     { label: "Planned",     cls: "badge-planned"  },
  booked:      { label: "Booked",      cls: "badge-booked"   },
  completed:   { label: "Completed",   cls: "badge-booked"   },
  archived:    { label: "Archived",    cls: "badge-archived" },
};

export function TripStatusBadge({ status }: { status: TripStatus }) {
  const { label, cls } = MAP[status] ?? MAP.draft;
  return <span className={clsx("badge", cls)}>{label}</span>;
}
