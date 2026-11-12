import {
  LoadingRegion,
  PageHeaderSkeleton,
} from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder rule rows. */
const RULE_ROWS = 5;

/**
 * Loading state for /urgency-rules. Mirrors UrgencyRulesWrapper: header with
 * the "Test" and "Add rule" buttons, then the numbered list of rules, each a
 * row with its index and an input-sized field.
 */
export function UrgencyRulesSkeleton() {
  return (
    <LoadingRegion label="urgency rules" className="flex min-h-0 flex-1">
      <div className="h-full min-w-0 flex-1 px-4 pt-8 pb-16 sm:px-8 md:pt-10">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
          <PageHeaderSkeleton
            actions={
              <>
                <Skeleton className="h-9 w-24" />
                <Skeleton className="h-9 w-28" />
              </>
            }
          />

          <div className="flex flex-col border bg-card shadow-xs">
            {Array.from({ length: RULE_ROWS }, (_, i) => (
              <div
                key={i}
                className="flex items-start gap-4 border-b px-4 py-3 last:border-b-0"
              >
                {/* Rule number column (w-8) */}
                <Skeleton className="mt-1 h-3 w-5" />
                <div className="flex min-w-0 flex-1 flex-col gap-1.5 pt-0.5">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-28" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </LoadingRegion>
  );
}
