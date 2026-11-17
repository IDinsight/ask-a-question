import { WorkspaceManagementSkeleton } from "@/components/features/workspace-management/components/WorkspaceManagementSkeleton";

/** Route-level Suspense fallback for /workspace-management: a skeleton shaped like the page. */
export default function Loading() {
  return <WorkspaceManagementSkeleton />;
}
