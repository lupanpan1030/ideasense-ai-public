"use client";

import { cn } from "@/lib/utils";

type AuthSimpleIllustrationProps = {
  className?: string;
  tone?: "info" | "success" | "warning";
};

export function AuthSimpleIllustration({
  className,
  tone = "info",
}: AuthSimpleIllustrationProps) {
  return (
    <div
      className={cn(
        "auth-simple-illustration",
        `auth-simple-illustration--${tone}`,
        className
      )}
      aria-hidden="true"
    >
      <div className="auth-simple-illustration__orb auth-simple-illustration__orb--large" />
      <div className="auth-simple-illustration__orb auth-simple-illustration__orb--small" />
      <div className="auth-simple-illustration__card auth-simple-illustration__card--primary">
        <span className="auth-simple-illustration__line auth-simple-illustration__line--short" />
        <span className="auth-simple-illustration__line" />
        <span className="auth-simple-illustration__line auth-simple-illustration__line--muted" />
      </div>
      <div className="auth-simple-illustration__card auth-simple-illustration__card--secondary">
        <span className="auth-simple-illustration__pill" />
        <span className="auth-simple-illustration__line auth-simple-illustration__line--short" />
      </div>
      <div className="auth-simple-illustration__anchor" />
    </div>
  );
}
