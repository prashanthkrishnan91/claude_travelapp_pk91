import { Skeleton } from "@/components/ui/Skeleton";

export default function DashboardLoading() {
  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="space-y-2">
          <Skeleton className="h-7 w-32 rounded-lg" />
          <Skeleton className="h-4 w-56 rounded-lg" />
        </div>
        <Skeleton className="h-9 w-24 rounded-xl" />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-6 flex items-start gap-4">
            <Skeleton className="w-11 h-11 rounded-xl shrink-0" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-20 rounded" />
              <Skeleton className="h-7 w-16 rounded" />
              <Skeleton className="h-3 w-28 rounded" />
            </div>
          </div>
        ))}
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Recent trips skeleton */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <Skeleton className="h-5 w-28 rounded" />
              <Skeleton className="h-4 w-14 rounded" />
            </div>
            <div className="divide-y divide-slate-100">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-start gap-4 px-6 py-4">
                  <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-40 rounded" />
                    <Skeleton className="h-3 w-24 rounded" />
                    <Skeleton className="h-3 w-48 rounded" />
                  </div>
                  <Skeleton className="h-5 w-16 rounded-full shrink-0" />
                </div>
              ))}
            </div>
          </div>

          {/* Quick actions skeleton */}
          <div className="card p-6">
            <Skeleton className="h-5 w-28 rounded mb-4" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-100">
                  <Skeleton className="w-9 h-9 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-4 w-20 rounded" />
                    <Skeleton className="h-3 w-32 rounded" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Points summary skeleton */}
        <div>
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-32 rounded" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
            <Skeleton className="h-24 w-full rounded-xl" />
            <div className="space-y-3">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="w-8 h-8 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-4 w-32 rounded" />
                    <Skeleton className="h-3 w-20 rounded" />
                  </div>
                  <div className="space-y-1 text-right shrink-0">
                    <Skeleton className="h-4 w-16 rounded" />
                    <Skeleton className="h-3 w-10 rounded ml-auto" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
