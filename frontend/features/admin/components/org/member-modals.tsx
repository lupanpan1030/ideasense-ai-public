import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AdminModal } from "@/features/admin/components/shared/admin-modal";
import {
  interpolateMemberMessage,
  type AdminMembersMessages,
  type OrgMember,
} from "@/features/admin/admin-members-view-model";

type RemoveMemberModalProps = {
  isRemoving: boolean;
  member: OrgMember | null;
  messages: AdminMembersMessages;
  onClose: () => void;
  onConfirm: () => void;
  removeTargetName: string;
};

export function RemoveMemberModal({
  isRemoving,
  member,
  messages,
  onClose,
  onConfirm,
  removeTargetName,
}: RemoveMemberModalProps) {
  if (!member) {
    return null;
  }

  return (
    <AdminModal
      labelledBy="remove-member-title"
      closeDisabled={isRemoving}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="remove-member-title">
            {messages.removeModal.title}
          </CardTitle>
          <CardDescription>
            {interpolateMemberMessage(messages.removeModal.description, {
              name: removeTargetName,
            })}
          </CardDescription>
        </CardHeader>
        <CardFooter className="admin-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isRemoving}
          >
            {messages.removeModal.cancel}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={isRemoving}>
            {isRemoving
              ? messages.removeModal.removing
              : messages.removeModal.confirm}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}
