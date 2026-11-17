import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/** Overview stat tiles: five across at xl, matching Overview's grid. */
const STAT_TILES = 5;
/** Period tabs in TabPanel (day, week, month, year, custom). */
const PERIOD_TABS = 5;

/**
 * Loading state for /dashboard. Mirrors DashboardWrapper on its default
 * Overview tab: header, the period TabPanel, stat tiles, the queries chart
 * beside the usage heatmap, then the top-content table.
 */
export function DashboardSkeleton() {
  return (
    <LoadingRegion
      label="dashboard"
      className="px-4 pt-8 pb-16 sm:px-8 md:pt-10"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <PageHeaderSkeleton />

        {/* TabPanel: segmented period control */}
        <div className="flex w-fit gap-1 bg-muted p-0.75">
          {Array.from({ length: PERIOD_TABS }, (_, i) => (
            <Skeleton key={i} className="h-8 w-16 bg-background" />
          ))}
        </div>

        {/* Overview */}
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
            {Array.from({ length: STAT_TILES }, (_, i) => (
              // Same height Overview uses for its own tile placeholders.
              <Skeleton key={i} className="h-[104px]" />
            ))}
          </div>

          <div className="flex flex-wrap gap-4">
            <SectionSkeleton
              className="flex-[2_1_520px]"
              bodyClassName="h-72"
            />
            <SectionSkeleton
              className="flex-[1_1_280px]"
              bodyClassName="h-72"
            />
          </div>

          <SectionSkeleton bodyClassName="h-56" />
        </div>
      </div>
    </LoadingRegion>
  );
}

/** A bordered card section: heading line, then the chart/table body. */
function SectionSkeleton({
  className = "",
  bodyClassName,
}: {
  className?: string;
  bodyClassName: string;
}) {
  return (
    <div
      className={`flex min-w-0 flex-col gap-4 border bg-card p-5 shadow-xs ${className}`}
    >
      <Skeleton className="h-5 w-40" />
      <Skeleton className={`w-full ${bodyClassName}`} />
    </div>
  );
}
