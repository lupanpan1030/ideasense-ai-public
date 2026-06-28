import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";

type InvitationDetailsResponse = {
  invitee_email: string;
};

const INVITE_DETAILS_FALLBACK = "Unable to load invitation details.";

export const fetchInvitationDetails = async (
  token: string
): Promise<InvitationDetailsResponse> => {
  const params = new URLSearchParams({ token });
  return apiClient.fetchJson<InvitationDetailsResponse>(
    `/invitations/details?${params.toString()}`
  );
};

export const getInviteDetailsErrorMessage = (error: unknown): string => {
  return getSafeErrorMessage(error, {
    default: INVITE_DETAILS_FALLBACK,
    notFound: "Invitation not found or expired.",
    unavailable: "Invitation details are unavailable. Try again shortly.",
  });
};
