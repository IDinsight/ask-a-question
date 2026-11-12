import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/** Connection tiles in ConnectionsGrid: four across at xl. */
const CONNECTION_TILES = 4;

/**
 * Loading state for /integrations. Mirrors IntegrationsWrapper: header, the
 * API key + daily limit cards side by side, then the "Connect a chat manager"
 * section and its grid of connection tiles.
 */
export function IntegrationsSkeleton() {
  return (
    <LoadingRegion
      label="integrations"
      className="px-4 pt-8 pb-16 sm:px-8 md:pt-10"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <PageHeaderSkeleton />

        <div className="grid gap-4 md:grid-cols-2">
          {/* KeyManagement */}
          <div className="flex flex-col gap-4 border bg-card p-5 shadow-xs">
            <Skeleton className="h-5 w-32" />
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9" />
              <Skeleton className="h-4 w-48" />
            </div>
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-9 w-36" />
            </div>
          </div>
          {/* DailyLimit */}
          <div className="flex flex-col gap-4 border bg-card p-5 shadow-xs">
            <Skeleton className="h-5 w-28" />
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>

        {/* Connect a chat manager */}
        <div className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-96 max-w-full" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: CONNECTION_TILES }, (_, i) => (
              <div
                key={i}
                className="flex flex-col gap-2 border bg-card p-4 shadow-xs"
              >
                <div className="flex items-center gap-3">
                  <Skeleton className="size-10" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
                <Skeleton className="mt-1 h-3 w-20" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </LoadingRegion>
  );
}
