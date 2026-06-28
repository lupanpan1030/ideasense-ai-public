import * as React from "react";

type SkeletonProps = React.HTMLAttributes<HTMLDivElement> & {
  style?: React.CSSProperties;
};

export function Skeleton({ className = "", ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={["skeleton", className].filter(Boolean).join(" ")}
      {...props}
    />
  );
}
