import { ContentSkeleton } from "@/components/features/content/components/ContentSkeleton";

/** Route-level Suspense fallback for /content: a skeleton shaped like the page. */
export default function Loading() {
  return <ContentSkeleton />;
}
