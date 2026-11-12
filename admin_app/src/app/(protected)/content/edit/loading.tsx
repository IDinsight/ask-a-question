import { ContentEditSkeleton } from "@/components/features/content/edit/components/ContentEditSkeleton";

/** Route-level Suspense fallback for /content/edit: a skeleton shaped like the page. */
export default function Loading() {
  return <ContentEditSkeleton />;
}
