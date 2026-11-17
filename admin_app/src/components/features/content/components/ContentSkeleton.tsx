import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder cards to show: two rows of three, the md-breakpoint grid. */
const PLACEHOLDER_CARDS = 6;

/**
 * Loading state for /content. Mirrors ContentWrapper: page header, the
 * CardsUtilityStrip (search + tag filter on the left, action buttons on the
 * right), then the bordered CardsGrid of ContentCards.
 */
export function ContentSkeleton() {
  return (
    <LoadingRegion label="content" className="flex min-h-0 flex-1">
      <div className="h-full min-w-0 flex-1 px-4 pt-8 sm:px-8 md:pt-10">
        <div className="mx-auto flex h-full w-full max-w-6xl flex-col">
          <PageHeaderSkeleton className="pb-6" />

          {/* CardsUtilityStrip */}
          <div className="flex w-full flex-wrap items-end justify-between gap-4 pb-4">
            <div className="flex flex-wrap items-end gap-3">
              <Skeleton className="h-9 w-55" />
              <Skeleton className="h-9 w-60" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Skeleton className="h-10 w-28" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="size-10" />
              <Skeleton className="h-10 w-20" />
            </div>
          </div>

          {/* CardsGrid */}
          <div className="w-full border bg-muted/30 p-2.5">
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3">
              {Array.from({ length: PLACEHOLDER_CARDS }, (_, i) => (
                <ContentCardSkeleton key={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </LoadingRegion>
  );
}

/** One ContentCard: number + title, a few lines of text, tags and votes. */
function ContentCardSkeleton() {
  return (
    // ContentCard has a fixed 210px height (CARD_HEIGHT).
    <div className="flex h-[210px] flex-col gap-3 border bg-card p-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-8" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
      </div>
      <div className="mt-auto flex items-center justify-between gap-2">
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-14" />
          <Skeleton className="h-5 w-16" />
        </div>
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  );
}
