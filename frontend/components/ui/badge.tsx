import * as React from "react";

type BadgeVariant =
  | "default"
  | "outline"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
};

const variantClasses: Record<BadgeVariant, string> = {
  default: "",
  outline: "badge--outline",
  secondary: "badge--secondary",
  success: "badge--success",
  warning: "badge--warning",
  danger: "badge--danger",
  info: "badge--info",
};

export function Badge({ variant = "default", className = "", ...props }: BadgeProps) {
  return (
    <span
      className={["badge", variantClasses[variant], className]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
}
