export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-shimmer rounded-lg ${className}`} />;
}

export function DashboardSkeleton() {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-8 py-5">
        <Skeleton className="h-5 w-64" />
        <Skeleton className="mt-2 h-4 w-40" />
      </header>
      <main className="flex-1 space-y-6 p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-5">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Skeleton className="h-[420px] xl:col-span-2" />
          <Skeleton className="h-[420px]" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-[260px]" />
          <Skeleton className="h-[260px]" />
        </div>
      </main>
    </div>
  );
}

export function BuildingSkeleton() {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-8 py-5">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="mt-3 h-5 w-56" />
        <Skeleton className="mt-2 h-4 w-40" />
      </header>
      <main className="flex-1 space-y-6 p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </main>
    </div>
  );
}
