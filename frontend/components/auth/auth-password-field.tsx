"use client";

import { useEffect, useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

type AuthPasswordFieldProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type"
> & {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  className?: string;
  inputClassName?: string;
  showPasswordLabel: string;
  hidePasswordLabel: string;
  onVisibilityChange?: (isVisible: boolean) => void;
};

export function AuthPasswordField({
  id,
  label,
  hint,
  error,
  className = "",
  inputClassName = "",
  showPasswordLabel,
  hidePasswordLabel,
  onVisibilityChange,
  ...props
}: AuthPasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  useEffect(() => {
    onVisibilityChange?.(isVisible);
  }, [isVisible, onVisibilityChange]);

  return (
    <div className={["field", className].filter(Boolean).join(" ")}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <div className="auth-password-control">
        <input
          id={id}
          type={isVisible ? "text" : "password"}
          className={cn(
            "input auth-password-control__input",
            error && "input--error",
            inputClassName
          )}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
          {...props}
        />
        <button
          type="button"
          className="auth-password-control__toggle"
          aria-label={isVisible ? hidePasswordLabel : showPasswordLabel}
          onClick={() => setIsVisible((current) => !current)}
          disabled={props.disabled}
        >
          {isVisible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
      {hint ? (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
