import type { ChangeEventHandler } from "react";
import Image from "next/image";

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
import type { OrgSettingsMessages } from "@/features/admin/org-settings-messages";

type AdminOrgLogoModalProps = {
  messages: OrgSettingsMessages;
  logoModalDescriptionId: string;
  logoPreviewUrl: string | null;
  logoFileName: string | null;
  logoNotice: string | null;
  hasLogoFile: boolean;
  onClose: () => void;
  onLogoFileChange: ChangeEventHandler<HTMLInputElement>;
  onLogoUpload: () => void;
};

export function AdminOrgLogoModal({
  messages,
  logoModalDescriptionId,
  logoPreviewUrl,
  logoFileName,
  logoNotice,
  hasLogoFile,
  onClose,
  onLogoFileChange,
  onLogoUpload,
}: AdminOrgLogoModalProps) {
  return (
    <AdminModal
      labelledBy="logo-modal-title"
      describedBy={logoModalDescriptionId}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="logo-modal-title">{messages.logo.title}</CardTitle>
          <CardDescription id={logoModalDescriptionId}>
            {messages.logo.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="stack">
          <div className="admin-logo-drop">
            {logoPreviewUrl ? (
              <Image
                className="admin-logo-drop__img"
                src={logoPreviewUrl}
                alt={messages.general.logoPreviewAlt}
                fill
                sizes="(max-width: 768px) 90vw, 520px"
                unoptimized
              />
            ) : (
              <div className="admin-logo-drop__placeholder">
                <span>{messages.logo.drop}</span>
                <span className="text-muted">
                  {messages.logo.placeholderHint}
                </span>
              </div>
            )}
          </div>
          <label className="admin-logo-input">
            <input
              type="file"
              accept="image/png,image/jpeg,image/svg+xml"
              onChange={onLogoFileChange}
            />
            <span>{logoFileName ?? messages.logo.chooseFile}</span>
          </label>
          {logoNotice ? (
            <div className="alert" role="status">
              <span>{logoNotice}</span>
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="admin-modal__footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            {messages.actions.cancel}
          </Button>
          <Button type="button" onClick={onLogoUpload} disabled={!hasLogoFile}>
            {messages.logo.upload}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}
