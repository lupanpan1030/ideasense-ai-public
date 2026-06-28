import { notFound } from "next/navigation";
import { AdminGuard } from "@/features/admin/admin-guard";
import { adminUiEnabled } from "@/lib/admin-config";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (!adminUiEnabled) {
    notFound();
  }
  return <AdminGuard>{children}</AdminGuard>;
}
