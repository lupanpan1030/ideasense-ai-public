"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";
export const focusRingOnDark =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#081223]";

export function SectionHeading({
  eyebrow,
  title,
  description,
  isZh,
  dark = false,
}: {
  eyebrow: string;
  title: string;
  description: string;
  isZh: boolean;
  dark?: boolean;
}) {
  return (
    <div>
      <p className={eyebrowClassName(isZh, dark)}>
        {eyebrow}
      </p>
      <h2 className={sectionTitleClassName(isZh, dark)}>
        {title}
      </h2>
      <p className={bodyClassName(isZh, dark)}>
        {description}
      </p>
    </div>
  );
}

export function eyebrowClassName(isZh: boolean, dark = false) {
  return cx(
    isZh
      ? "text-[13px] font-medium tracking-[0.04em]"
      : "text-xs uppercase tracking-[0.24em]",
    dark ? "text-[#93c5fd]" : "text-[#2563eb]"
  );
}

export function microLabelClassName(isZh: boolean, dark = false) {
  return cx(
    isZh
      ? "text-[12px] font-medium tracking-[0.03em]"
      : "text-[11px] uppercase tracking-[0.22em]",
    dark ? "text-[#93c5fd]" : "text-[#2563eb]"
  );
}

export function neutralMicroLabelClassName(isZh: boolean) {
  return isZh
    ? "text-[12px] font-medium tracking-[0.02em] text-[#64748b]"
    : "text-[11px] uppercase tracking-[0.18em] text-[#64748b]";
}

export function heroTitleClassName(isZh: boolean) {
  return cx(
    "mt-8 font-semibold text-[#0f172a]",
    isZh
      ? "max-w-[11em] text-[clamp(2.4rem,4.8vw,4.35rem)] leading-[1.16] tracking-[-0.022em]"
      : "text-[clamp(3.3rem,8.6vw,7rem)] leading-[0.92] tracking-[-0.06em]"
  );
}

export function sectionTitleClassName(isZh: boolean, dark = false) {
  return cx(
    "mt-5 font-semibold",
    isZh
      ? "text-[clamp(1.95rem,3.8vw,3.2rem)] leading-[1.2] tracking-[-0.018em]"
      : "text-4xl leading-[0.96] tracking-[-0.05em] md:text-6xl",
    dark ? "text-white" : "text-[#0f172a]"
  );
}

export function bodyClassName(isZh: boolean, dark = false) {
  return cx(
    "mt-5 md:text-lg",
    isZh ? "text-[15px] leading-[1.9] md:text-[17px]" : "text-base leading-relaxed",
    dark ? "text-white/68" : "text-[#475569]"
  );
}

export function SectionReveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ y: 18 }}
      whileInView={{ y: 0 }}
      viewport={{ once: true, amount: 0.28 }}
      transition={{ duration: 0.68, ease: EASE_OUT, delay }}
    >
      {children}
    </motion.div>
  );
}
