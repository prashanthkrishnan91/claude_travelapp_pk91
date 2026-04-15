import { Skeleton } from "@/components/ui/Skeleton";

export default function TripsLoading() {
  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="space-y-2">
          <Skeleton className="h-7 w-24 rounded-lg" />
          <Skeleton className="h-4 w-32 rounded-lg" />
        </div>
        <Skeleton className="h-9 w-24 rounded-xl" />
      </div>

      {/* Active trips */}
      <div className="space-y-8">
        <div>
          <Skeleton className="h-3 w-12 rounded mb-3 ml-1" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <Skeleton className="h-4 w-36 rounded" />
                  <Skeleton className="h-5 w-16 rounded-full shrink-0" />
                </div>
                <Skeleton className="h-4 w-28 rounded" />
                <div className="flex gap-3">
                  <Skeleton className="h-3 w-24 rounded" />
                  <Skeleton className="h-3 w-16 rounded" />
                </div>
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <Skeleton className="h-3 w-12 rounded" />
                  <Skeleton className="h-5 w-20 rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
