import * as React from "react";

type CardVariant = "default" | "soft" | "alert";

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: CardVariant;
};

const variantClasses: Record<CardVariant, string> = {
  default: "",
  soft: "card--soft",
  alert: "card--alert",
};

export function Card({ variant = "default", className = "", ...props }: CardProps) {
  return (
    <div
      className={["card", variantClasses[variant], className]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
}

export function CardHeader({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["card__header", className].filter(Boolean).join(" ")} {...props} />
  );
}

export function CardTitle({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={["card__title", className].filter(Boolean).join(" ")} {...props} />
  );
}

export function CardDescription({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={["card__description", className].filter(Boolean).join(" ")}
      {...props}
    />
  );
}

export function CardContent({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["card__content", className].filter(Boolean).join(" ")} {...props} />
  );
}

export function CardFooter({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["card__footer", className].filter(Boolean).join(" ")} {...props} />
  );
}
