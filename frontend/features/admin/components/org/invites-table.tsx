"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError, apiClient } from "@/lib/api/client";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import {
  buildInvitesQuery,
  DEFAULT_INVITES_LIMIT,
  ROLE_FILTER_VALUES,
  ROLE_VALUES,
  STATUS_FILTER_VALUES,
  type AdminInvitesMessages,
  type InviteCreateResponse,
  type InviteRole,
  type InvitesResponse,
  type OrgInvite,
  type RoleFilter,
  type StatusFilter,
} from "@/features/admin/admin-invites-view-model";
import {
  CreateInviteModal,
  RevokeInviteModal,
} from "@/features/admin/components/org/invite-modals";
import { InvitesTableSurface } from "@/features/admin/components/org/invites-table-surface";

const getInvitesErrorMessage = (
  error: unknown,
  messages: AdminInvitesMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status >= 500) {
      return messages.errors.unavailable;
    }
  }
  return messages.errors.loadFailed;
};

const getInviteActionErrorMessage = (
  error: unknown,
  messages: AdminInvitesMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status === 409) {
      return messages.errors.inviteConflict;
    }
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

const fetchInvites = async (
  page: number,
  roleFilter: RoleFilter,
  statusFilter: StatusFilter,
  query: string
): Promise<InvitesResponse> => {
  const queryString = buildInvitesQuery(page, roleFilter, statusFilter, query);
  const url = queryString
    ? `/admin-api/org/invites?${queryString}`
    : "/admin-api/org/invites";
  return apiClient.fetchJson<InvitesResponse>(url);
};

const createInvite = async (
  email: string,
  role: InviteRole
): Promise<InviteCreateResponse> =>
  apiClient.postJson<InviteCreateResponse>("/admin-api/org/invites", {
    email,
    role,
  });

const revokeInvite = async (inviteId: string): Promise<OrgInvite> =>
  apiClient.fetchJson(`/admin-api/org/invites/${inviteId}`, {
    method: "PATCH",
  });

export function InvitesTable() {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminInvites;
  const roleLabels = appMessages.adminShell.roles;
  const [invites, setInvites] = useState<OrgInvite[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalView, setModalView] = useState<"form" | "success">("form");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InviteRole>("student");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successToken, setSuccessToken] = useState<string | null>(null);
  const [successLink, setSuccessLink] = useState<string | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);

  const [inviteToRevoke, setInviteToRevoke] = useState<OrgInvite | null>(null);
  const [isRevoking, setIsRevoking] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setPage(1);
  }, [query, roleFilter, statusFilter]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchInvites(page, roleFilter, statusFilter, debouncedQuery)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setInvites(response.invites ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getInvitesErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [page, roleFilter, statusFilter, debouncedQuery, messages]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / DEFAULT_INVITES_LIMIT)),
    [total]
  );
  const currentPage = useMemo(
    () => Math.min(totalPages, Math.max(page, 1)),
    [page, totalPages]
  );
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;
  const pageStart =
    total === 0 ? 0 : (currentPage - 1) * DEFAULT_INVITES_LIMIT + 1;
  const pageEnd = Math.min(currentPage * DEFAULT_INVITES_LIMIT, total);
  const roleFilterOptions = ROLE_FILTER_VALUES.map((value) => ({
    value,
    label: messages.filters.roleOptions[value],
  }));
  const roleOptions = ROLE_VALUES.map((value) => ({
    value,
    label: roleLabels[value] ?? value,
  }));
  const statusFilterOptions = STATUS_FILTER_VALUES.map((value) => ({
    value,
    label: messages.filters.statusOptions[value],
  }));

  const resetModalState = () => {
    setInviteEmail("");
    setInviteRole("student");
    setFormError(null);
    setSubmitError(null);
    setModalView("form");
    setSuccessToken(null);
    setSuccessLink(null);
    setCopyNotice(null);
  };

  const handleOpenModal = () => {
    resetModalState();
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    if (isSubmitting) {
      return;
    }
    setIsModalOpen(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    const trimmedEmail = inviteEmail.trim();
    if (!trimmedEmail) {
      setFormError(messages.errors.emailRequired);
      setSubmitError(null);
      return;
    }
    setFormError(null);
    setSubmitError(null);
    setIsSubmitting(true);
    setActionError(null);

    try {
      const response = await createInvite(trimmedEmail, inviteRole);
      if (response.status === "restored") {
        setIsModalOpen(false);
        setToastMessage(messages.toasts.restored);
      } else {
        setModalView("success");
        setSuccessToken(response.token ?? null);
        setSuccessLink(response.invite_link ?? null);
      }
      setPage(1);
      await fetchInvites(1, roleFilter, statusFilter, debouncedQuery).then(
        (updated) => {
          setInvites(updated.invites ?? []);
          setTotal(updated.total ?? 0);
        }
      );
    } catch (error) {
      setSubmitError(getInviteActionErrorMessage(error, messages));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = async () => {
    if (!successLink) {
      return;
    }
    try {
      await navigator.clipboard.writeText(successLink);
      setCopyNotice(messages.toasts.copied);
    } catch {
      setCopyNotice(messages.toasts.copyFailed);
    }
  };

  const handleRevoke = async () => {
    if (!inviteToRevoke) {
      return;
    }
    setIsRevoking(true);
    setActionError(null);
    try {
      await revokeInvite(inviteToRevoke.id);
      setToastMessage(messages.toasts.inviteRevoked);
      setInvites((prev) =>
        prev.map((invite) =>
          invite.id === inviteToRevoke.id
            ? { ...invite, status: "revoked" }
            : invite
        )
      );
    } catch (error) {
      setActionError(getInviteActionErrorMessage(error, messages));
    } finally {
      setIsRevoking(false);
      setInviteToRevoke(null);
    }
  };

  return (
    <>
      <InvitesTableSurface
        actionError={actionError}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        currentPage={currentPage}
        invites={invites}
        isLoading={isLoading}
        loadError={loadError}
        locale={locale}
        messages={messages}
        onOpenCreateModal={handleOpenModal}
        onPageChange={setPage}
        onQueryChange={setQuery}
        onRequestRevoke={setInviteToRevoke}
        onRoleFilterChange={setRoleFilter}
        onStatusFilterChange={setStatusFilter}
        page={page}
        pageEnd={pageEnd}
        pageStart={pageStart}
        query={query}
        roleFilter={roleFilter}
        roleFilterOptions={roleFilterOptions}
        roleLabels={roleLabels}
        statusFilter={statusFilter}
        statusFilterOptions={statusFilterOptions}
        toastMessage={toastMessage}
        total={total}
        totalPages={totalPages}
      />
      <CreateInviteModal
        copyNotice={copyNotice}
        formError={formError}
        inviteEmail={inviteEmail}
        inviteRole={inviteRole}
        isOpen={isModalOpen}
        isSubmitting={isSubmitting}
        messages={messages}
        modalView={modalView}
        onClose={handleCloseModal}
        onCopy={handleCopy}
        onEmailChange={setInviteEmail}
        onRoleChange={setInviteRole}
        onSubmit={handleSubmit}
        roleOptions={roleOptions}
        submitError={submitError}
        successLink={successLink}
        successToken={successToken}
      />
      <RevokeInviteModal
        invite={inviteToRevoke}
        isRevoking={isRevoking}
        messages={messages}
        onClose={() => setInviteToRevoke(null)}
        onConfirm={handleRevoke}
      />
    </>
  );
}
