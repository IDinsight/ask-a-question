import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder user rows. */
const USER_ROWS = 4;

/**
 * Loading state for /workspace-management. Mirrors
 * WorkspaceManagementWrapper: workspace name header with the two "add" buttons,
 * then the bordered users section with one UserCard row per user.
 */
export function WorkspaceManagementSkeleton() {
  return (
    <LoadingRegion
      label="workspace"
      className="px-4 pt-8 pb-16 sm:px-8 md:pt-10"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <PageHeaderSkeleton
          actions={
            <>
              <Skeleton className="h-9 w-36" />
              <Skeleton className="h-9 w-28" />
            </>
          }
        />

        <div className="border bg-card shadow-xs">
          {/* Section heading: "Users" + count */}
          <div className="flex items-center gap-2 border-b px-4 py-3">
            <Skeleton className="h-5 w-14" />
            <Skeleton className="h-4 w-6" />
          </div>
          <div>
            {Array.from({ length: USER_ROWS }, (_, i) => (
              <div
                key={i}
                className="flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
              >
                {/* UserCard: avatar, name + role */}
                <Skeleton className="size-9 rounded-full" />
                <div className="flex flex-1 flex-col gap-1.5">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </LoadingRegion>
  );
}
