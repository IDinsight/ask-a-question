import { LoadingRegion } from "@/components/common/PageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Loading state for /content/edit. Mirrors ContentEditWrapper: back button +
 * title, then ContentBox (title input, text area, tags field, save button).
 */
export function ContentEditSkeleton() {
  return (
    <LoadingRegion
      label="content editor"
      className="flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-8 md:py-10"
    >
      {/* Header: icon button + "Edit content #N" */}
      <div className="flex items-center gap-2">
        <Skeleton className="size-9" />
        <Skeleton className="h-8 w-48" />
      </div>

      {/* ContentBox */}
      <div className="border bg-card p-6">
        <div className="flex flex-col gap-5">
          <FieldSkeleton labelWidth="w-12" inputClassName="h-9" />
          <FieldSkeleton labelWidth="w-16" inputClassName="h-72" />
          <FieldSkeleton labelWidth="w-10" inputClassName="h-9 max-w-125" />
        </div>
        <div className="mt-6">
          <Skeleton className="h-10 w-24" />
        </div>
      </div>
    </LoadingRegion>
  );
}

function FieldSkeleton({
  labelWidth,
  inputClassName,
}: {
  labelWidth: string;
  inputClassName: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className={`h-4 ${labelWidth}`} />
      <Skeleton className={`w-full ${inputClassName}`} />
    </div>
  );
}
