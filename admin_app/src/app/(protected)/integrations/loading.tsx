import { IntegrationsSkeleton } from "@/components/features/integrations/components/IntegrationsSkeleton";

/** Route-level Suspense fallback for /integrations: a skeleton shaped like the page. */
export default function Loading() {
  return <IntegrationsSkeleton />;
}
