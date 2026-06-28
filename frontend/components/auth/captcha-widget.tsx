"use client";

import { useEffect, useRef } from "react";
import Script from "next/script";

const resolveProvider = (): "hcaptcha" | "recaptcha" => {
  const raw = process.env.NEXT_PUBLIC_CAPTCHA_PROVIDER?.trim().toLowerCase();
  return raw === "recaptcha" ? "recaptcha" : "hcaptcha";
};

const resolveSiteKey = () =>
  process.env.NEXT_PUBLIC_CAPTCHA_SITE_KEY?.trim() ?? "";

export const isCaptchaEnabled = () => Boolean(resolveSiteKey());

type CaptchaWidgetProps = {
  onToken: (token: string | null) => void;
};

declare global {
  interface Window {
    hcaptcha?: {
      render: (container: HTMLElement, params: Record<string, unknown>) => number;
      reset: (widgetId?: number) => void;
      remove: (widgetId?: number) => void;
    };
    grecaptcha?: {
      render: (container: HTMLElement, params: Record<string, unknown>) => number;
      reset: (widgetId?: number) => void;
    };
    __captchaOnLoad?: () => void;
  }
}

const buildScriptSrc = (provider: "hcaptcha" | "recaptcha") => {
  if (provider === "recaptcha") {
    return "https://www.google.com/recaptcha/api.js?render=explicit&onload=__captchaOnLoad";
  }
  return "https://js.hcaptcha.com/1/api.js?render=explicit&onload=__captchaOnLoad";
};

export function CaptchaWidget({ onToken }: CaptchaWidgetProps) {
  const provider = resolveProvider();
  const siteKey = resolveSiteKey();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<number | null>(null);
  const tokenHandlerRef = useRef(onToken);

  useEffect(() => {
    tokenHandlerRef.current = onToken;
  }, [onToken]);

  useEffect(() => {
    if (!siteKey) {
      return;
    }
    const renderWidget = () => {
      const container = containerRef.current;
      if (!container || widgetIdRef.current !== null) {
        return;
      }
      if (provider === "recaptcha" && window.grecaptcha) {
        widgetIdRef.current = window.grecaptcha.render(container, {
          sitekey: siteKey,
          callback: (token: string) => tokenHandlerRef.current(token),
          "expired-callback": () => tokenHandlerRef.current(null),
          "error-callback": () => tokenHandlerRef.current(null),
        });
        return;
      }
      if (provider === "hcaptcha" && window.hcaptcha) {
        widgetIdRef.current = window.hcaptcha.render(container, {
          sitekey: siteKey,
          callback: (token: string) => tokenHandlerRef.current(token),
          "expired-callback": () => tokenHandlerRef.current(null),
          "error-callback": () => tokenHandlerRef.current(null),
        });
      }
    };

    if (provider === "recaptcha") {
      if (window.grecaptcha) {
        renderWidget();
      } else {
        window.__captchaOnLoad = renderWidget;
      }
    } else if (window.hcaptcha) {
      renderWidget();
    } else {
      window.__captchaOnLoad = renderWidget;
    }

    return () => {
      if (provider === "recaptcha" && window.grecaptcha) {
        window.grecaptcha.reset(widgetIdRef.current ?? undefined);
      }
      if (provider === "hcaptcha" && window.hcaptcha) {
        window.hcaptcha.reset(widgetIdRef.current ?? undefined);
        window.hcaptcha.remove(widgetIdRef.current ?? undefined);
      }
      widgetIdRef.current = null;
    };
  }, [provider, siteKey]);

  if (!siteKey) {
    return (
      <div className="captcha-placeholder">
        Captcha is not configured. Contact support if this persists.
      </div>
    );
  }

  return (
    <div className="captcha-shell">
      <Script src={buildScriptSrc(provider)} strategy="afterInteractive" />
      <div className="captcha-widget" ref={containerRef} />
    </div>
  );
}
