import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/storage/token";

type LoginPayload = {
  email: string;
  password: string;
  captcha_token?: string;
};

type DevLoginPayload = {
  email: string;
};

type RegisterPayload = {
  email: string;
  password: string;
  full_name?: string;
  captcha_token?: string;
};

type TokenResponse = {
  access_token: string;
  token_type?: string;
};

const normalizeEmail = (email: string) => email.trim();

export async function loginWithEmail(
  payload: LoginPayload,
  options?: { persist?: boolean }
): Promise<TokenResponse> {
  const response = await apiClient.postJson<TokenResponse>("/auth/login", {
    ...payload,
    email: normalizeEmail(payload.email),
  });

  tokenStorage.setToken(response.access_token, options);
  return response;
}

export async function devLoginWithEmail(
  payload: DevLoginPayload,
  options?: { persist?: boolean }
): Promise<TokenResponse> {
  const response = await apiClient.postJson<TokenResponse>("/auth/dev-login", {
    ...payload,
    email: normalizeEmail(payload.email),
  });

  tokenStorage.setToken(response.access_token, options);
  return response;
}

export async function registerWithEmail(
  payload: RegisterPayload,
  options?: { persist?: boolean }
): Promise<TokenResponse> {
  const response = await apiClient.postJson<TokenResponse>("/auth/register", {
    ...payload,
    email: normalizeEmail(payload.email),
  });

  tokenStorage.setToken(response.access_token, options);
  return response;
}
