import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Fallback for signed-in pages that don't define their own loading.tsx.
 * Every current feature has a page-shaped skeleton next to its page.tsx; this
 * generic one (header + content block) covers anything added later.
 */
export default function Loading() {
  return (
    <LoadingRegion label="page" className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <PageHeaderSkeleton />
        <Skeleton className="h-96 w-full" />
      </div>
    </LoadingRegion>
  );
}
