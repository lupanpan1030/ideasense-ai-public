import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AdminModal } from "@/features/admin/components/shared/admin-modal";
import type {
  AdminInvitesMessages,
  InviteRole,
  OrgInvite,
} from "@/features/admin/admin-invites-view-model";

type InviteRoleOption = {
  value: InviteRole;
  label: string;
};

type CreateInviteModalProps = {
  copyNotice: string | null;
  formError: string | null;
  inviteEmail: string;
  inviteRole: InviteRole;
  isOpen: boolean;
  isSubmitting: boolean;
  messages: AdminInvitesMessages;
  modalView: "form" | "success";
  onClose: () => void;
  onCopy: () => void;
  onEmailChange: (value: string) => void;
  onRoleChange: (value: InviteRole) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  roleOptions: InviteRoleOption[];
  submitError: string | null;
  successLink: string | null;
  successToken: string | null;
};

export function CreateInviteModal({
  copyNotice,
  formError,
  inviteEmail,
  inviteRole,
  isOpen,
  isSubmitting,
  messages,
  modalView,
  onClose,
  onCopy,
  onEmailChange,
  onRoleChange,
  onSubmit,
  roleOptions,
  submitError,
  successLink,
  successToken,
}: CreateInviteModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <AdminModal
      labelledBy="invite-modal-title"
      closeDisabled={isSubmitting}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="invite-modal-title">
            {modalView === "success"
              ? messages.createModal.readyTitle
              : messages.createModal.createTitle}
          </CardTitle>
          <CardDescription>
            {modalView === "success"
              ? messages.createModal.readyDescription
              : messages.createModal.createDescription}
          </CardDescription>
        </CardHeader>
        {modalView === "success" ? (
          <>
            <CardContent className="stack">
              <div className="field">
                <label className="field__label" htmlFor="invite-link">
                  {messages.createModal.inviteLink}
                </label>
                <input
                  id="invite-link"
                  className="input"
                  readOnly
                  value={successLink ?? "--"}
                />
              </div>
              {successToken ? (
                <div className="admin-invite__token">
                  {messages.createModal.tokenLabel}: <span>{successToken}</span>
                </div>
              ) : null}
              {copyNotice ? (
                <div className="alert" role="status">
                  <span>{copyNotice}</span>
                </div>
              ) : null}
            </CardContent>
            <CardFooter className="admin-modal__footer">
              <Button type="button" variant="secondary" onClick={onClose}>
                {messages.createModal.close}
              </Button>
              <Button type="button" onClick={onCopy}>
                {messages.createModal.copyLink}
              </Button>
            </CardFooter>
          </>
        ) : (
          <form className="stack" onSubmit={onSubmit}>
            <CardContent className="stack">
              <div className="field">
                <label className="field__label" htmlFor="invite-email">
                  {messages.createModal.inviteeEmail}
                </label>
                <input
                  id="invite-email"
                  type="email"
                  className="input"
                  placeholder={messages.createModal.inviteeEmailPlaceholder}
                  value={inviteEmail}
                  onChange={(event) => onEmailChange(event.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="invite-role">
                  {messages.createModal.role}
                </label>
                <select
                  id="invite-role"
                  className="input"
                  value={inviteRole}
                  onChange={(event) =>
                    onRoleChange(event.target.value as InviteRole)
                  }
                  disabled={isSubmitting}
                >
                  {roleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              {formError ? (
                <div className="alert" role="alert">
                  <span>{formError}</span>
                </div>
              ) : null}
              {submitError ? (
                <div className="alert" role="alert">
                  <span>{submitError}</span>
                </div>
              ) : null}
            </CardContent>
            <CardFooter className="admin-modal__footer">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={isSubmitting}
              >
                {messages.createModal.cancel}
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting
                  ? messages.createModal.sending
                  : messages.createModal.createInvite}
              </Button>
            </CardFooter>
          </form>
        )}
      </Card>
    </AdminModal>
  );
}

type RevokeInviteModalProps = {
  invite: OrgInvite | null;
  isRevoking: boolean;
  messages: AdminInvitesMessages;
  onClose: () => void;
  onConfirm: () => void;
};

export function RevokeInviteModal({
  invite,
  isRevoking,
  messages,
  onClose,
  onConfirm,
}: RevokeInviteModalProps) {
  if (!invite) {
    return null;
  }

  return (
    <AdminModal
      labelledBy="revoke-invite-title"
      closeDisabled={isRevoking}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="revoke-invite-title">
            {messages.revokeModal.title}
          </CardTitle>
          <CardDescription>{messages.revokeModal.description}</CardDescription>
        </CardHeader>
        <CardFooter className="admin-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isRevoking}
          >
            {messages.revokeModal.cancel}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={isRevoking}>
            {isRevoking
              ? messages.revokeModal.revoking
              : messages.revokeModal.confirm}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}
