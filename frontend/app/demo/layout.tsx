import type { ReactNode } from "react";
import { Sidebar } from "@/components/workspace/Sidebar";
import { WorkspaceTopBar } from "@/components/workspace/WorkspaceTopBar";

export default function WorkspaceLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface-muted md:flex">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <WorkspaceTopBar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
