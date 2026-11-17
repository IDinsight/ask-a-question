import WorkspaceManagementWrapper from "@/components/features/workspace-management/WorkspaceManagementWrapper";

/** Routing layer only: all UI, state and data fetching live in <WorkspaceManagementWrapper />. */
export default function Page() {
  return <WorkspaceManagementWrapper />;
}
