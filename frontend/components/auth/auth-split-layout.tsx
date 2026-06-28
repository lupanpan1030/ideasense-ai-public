"use client";

import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { AuthSimpleIllustration } from "@/components/auth/auth-simple-illustration";
import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import {
  AnimatedCharactersLoginPage,
  type AnimatedCharactersActiveField,
} from "@/components/ui/animated-characters-login-page";
import { Badge } from "@/components/ui/badge";
import { useAppLocale } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type AuthSplitLayoutProps = {
  badge: string;
  title: string;
  subtitle: string;
  visualTitle: string;
  visualDescription: string;
  visualNoteTitle?: string;
  visualNoteDescription?: string;
  mode?: "login" | "register" | "neutral";
  visualVariant?: "full" | "simple";
  simpleTone?: "info" | "success" | "warning";
  activeField?: AnimatedCharactersActiveField;
  isPasswordVisible?: boolean;
  hasPasswordValue?: boolean;
  showSupportLinks?: boolean;
  children: ReactNode;
  className?: string;
};

export function AuthSplitLayout({
  badge,
  title,
  subtitle,
  visualTitle,
  visualDescription,
  visualNoteTitle,
  visualNoteDescription,
  mode = "login",
  visualVariant = "full",
  simpleTone = "info",
  activeField = null,
  isPasswordVisible = false,
  hasPasswordValue = false,
  showSupportLinks = false,
  children,
  className,
}: AuthSplitLayoutProps) {
  const isZh = useAppLocale() === "zh";

  return (
    <div className={cn("auth-page auth-page--split", className)}>
      <div
        className={cn(
          "auth-shell auth-shell--split",
          visualVariant === "full" && "auth-shell--split-full"
        )}
      >
        <aside
          className={cn(
            "auth-visual",
            mode === "register" && "auth-visual--register",
            mode === "neutral" && "auth-visual--neutral",
            visualVariant === "simple" && "auth-visual--simple"
          )}
        >
          <div className="auth-visual__mesh auth-visual__mesh--primary" />
          <div className="auth-visual__mesh auth-visual__mesh--secondary" />

          <div className="auth-visual__brand">
            <div className="auth-visual__brand-mark">
              <Sparkles className="size-4" />
            </div>
            <span>IdeaSense AI</span>
          </div>

          <div className="auth-visual__copy">
            <Badge variant="secondary" className="auth-visual__badge">
              {badge}
            </Badge>
            <h2 className="auth-visual__title">{visualTitle}</h2>
            <p className="auth-visual__description">{visualDescription}</p>
          </div>

          <div className="auth-visual__scene-shell">
            {visualVariant === "full" ? (
              <AnimatedCharactersLoginPage
                className="auth-visual__scene"
                mode={mode === "register" ? "register" : "login"}
                activeField={activeField}
                isPasswordVisible={isPasswordVisible}
                hasPasswordValue={hasPasswordValue}
              />
            ) : (
              <AuthSimpleIllustration
                className="auth-visual__scene auth-visual__scene--simple"
                tone={simpleTone}
              />
            )}
          </div>

          {visualNoteTitle || visualNoteDescription ? (
            <div className="auth-visual__note">
              {visualNoteTitle ? (
                <p className="auth-visual__note-title">{visualNoteTitle}</p>
              ) : null}
              {visualNoteDescription ? (
                <p className="auth-visual__note-description">
                  {visualNoteDescription}
                </p>
              ) : null}
            </div>
          ) : null}
        </aside>

        <section
          className={cn(
            "auth-content",
            visualVariant === "full" && "auth-content--split-full"
          )}
        >
          <div className="auth-content__intro">
            <Badge variant="info">{badge}</Badge>
            <h1 className="page-title">{title}</h1>
            <p className="page-subtitle">{subtitle}</p>
          </div>

          <div
            className={cn(
              "auth-content__stack",
              visualVariant === "full" && "auth-content__stack--split-full"
            )}
          >
            {children}
          </div>

          {showSupportLinks ? (
            <MarketingSupportLinks isZh={isZh} variant="panel" />
          ) : null}
        </section>
      </div>
    </div>
  );
}
