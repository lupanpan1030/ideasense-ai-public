import { redirect } from "next/navigation";
import { ChatPanels } from "@/features/chat/chat-panels";
import { normalizeProjectId } from "@/features/projects/project-id";
import { ChatPermissionGuard } from "@/features/projects/chat-permission-guard";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

type ChatPageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ChatPage({ params }: ChatPageProps) {
  const locale = await getRequestLocale();
  const resolvedParams = await params;
  const projectId = normalizeProjectId(resolvedParams.projectId);
  if (!projectId) {
    redirect(buildLocalePath(locale, "/projects"));
  }
  return (
    <ChatPermissionGuard projectId={projectId}>
      <div className="page page--chat">
        <ChatPanels projectId={projectId} />
      </div>
    </ChatPermissionGuard>
  );
}
