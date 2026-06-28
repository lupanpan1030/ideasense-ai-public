import { redirect } from "next/navigation";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

export default async function AdminAssignmentsPage() {
  const locale = await getRequestLocale();
  redirect(buildLocalePath(locale, "/admin/org/mentor-assignments"));
}
