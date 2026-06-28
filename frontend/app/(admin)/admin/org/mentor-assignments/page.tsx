import { MentorAssignmentsTable } from "@/features/admin/components/org/mentor-assignments-table";
import { getRequestLocale } from "@/lib/i18n/request-locale";
import { APP_MESSAGES } from "@/lib/i18n/messages";

export default async function AdminMentorAssignmentsPage() {
  const locale = await getRequestLocale();
  const messages = APP_MESSAGES[locale].adminMentorAssignments.page;

  return (
    <div className="page">
      <div className="page-header">
        <div className="stack-sm">
          <p className="eyebrow">{messages.eyebrow}</p>
          <h1 className="page-title">{messages.title}</h1>
          <p className="page-subtitle">{messages.subtitle}</p>
        </div>
      </div>
      <MentorAssignmentsTable />
    </div>
  );
}
