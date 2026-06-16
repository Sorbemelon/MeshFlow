import type { ReactNode } from "react";
import { Sidebar } from "@/components/workspace/Sidebar";
import { WorkspaceRouteGuard } from "@/components/workspace/WorkspaceRouteGuard";
import { WorkspaceSessionProvider } from "@/components/workspace/WorkspaceSessionProvider";
import { WorkspaceTopBar } from "@/components/workspace/WorkspaceTopBar";

export default function WorkspaceLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <WorkspaceSessionProvider>
      <div className="min-h-screen bg-surface-muted md:flex">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <WorkspaceTopBar />
          <main className="min-w-0 flex-1">
            <WorkspaceRouteGuard>{children}</WorkspaceRouteGuard>
          </main>
        </div>
      </div>
    </WorkspaceSessionProvider>
  );
}
