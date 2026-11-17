import { DashboardSkeleton } from "@/components/features/dashboard/components/DashboardSkeleton";

/** Route-level Suspense fallback for /dashboard: a skeleton shaped like the page. */
export default function Loading() {
  return <DashboardSkeleton />;
}
