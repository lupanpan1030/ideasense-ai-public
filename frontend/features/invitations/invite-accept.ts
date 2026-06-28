import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { inviteTokenStorage } from "@/lib/storage/invite";
import { orgStorage } from "@/lib/storage/org";

type InvitationAcceptResponse = {
  status: "accepted";
  org_id: string;
};

export type InviteAcceptResult =
  | { status: "skipped" }
  | { status: "accepted"; orgId: string }
  | { status: "error"; message: string };

const INVITE_ACCEPT_FALLBACK = "Unable to accept invitation.";
const INVITE_ERROR_PREFIX = "Failed to join organization: ";

export const INVITE_ERROR_QUERY_KEY = "invite_error";

const getInviteAcceptErrorMessage = (error: unknown): string => {
  return getSafeErrorMessage(error, {
    accessDenied: "You do not have access to accept this invitation.",
    default: INVITE_ACCEPT_FALLBACK,
    notFound: "Invitation not found or expired.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Invitation service is unavailable. Try again shortly.",
  });
};

export const buildInviteErrorMessage = (detail: string): string => {
  const trimmed = detail.trim();
  return `${INVITE_ERROR_PREFIX}${trimmed || INVITE_ACCEPT_FALLBACK}`;
};

export const acceptInvitationIfPresent =
  async (): Promise<InviteAcceptResult> => {
    const token = inviteTokenStorage.getToken();
    if (!token) {
      return { status: "skipped" };
    }

    try {
      const response = await apiClient.postJson<InvitationAcceptResponse>(
        "/invitations/accept",
        { token }
      );
      inviteTokenStorage.clearToken();
      if (response.org_id) {
        orgStorage.setOrgId(response.org_id);
      }
      return { status: "accepted", orgId: response.org_id };
    } catch (error) {
      const message = getInviteAcceptErrorMessage(error);
      inviteTokenStorage.clearToken();
      return { status: "error", message };
    }
  };
