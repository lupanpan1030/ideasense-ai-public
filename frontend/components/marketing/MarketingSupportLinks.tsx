"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

type MarketingSupportLinksProps = {
  isZh: boolean;
  tone?: "light" | "dark";
  variant?: "dock" | "panel";
  className?: string;
};

const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";
const focusRingOnDark =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#081223]";

const stripLocalePrefix = (pathname: string) => {
  if (pathname === "/en" || pathname === "/zh") {
    return "/";
  }

  if (pathname.startsWith("/en/") || pathname.startsWith("/zh/")) {
    return pathname.slice(3);
  }

  return pathname || "/";
};

export function MarketingSupportLinks({
  isZh,
  tone = "light",
  variant = "dock",
  className,
}: MarketingSupportLinksProps) {
  const locale = useAppLocale();
  const pathname = usePathname() ?? "/";
  const normalizedPathname = stripLocalePrefix(pathname);
  const links = [
    { href: "/", label: isZh ? "首页" : "Home" },
    { href: "/methodology", label: isZh ? "方法论" : "Methodology" },
    { href: "/sample", label: isZh ? "示例工作区" : "Sample Workspace" },
    { href: "/sample-report", label: isZh ? "示例报告" : "Sample Report" },
    { href: "/privacy", label: isZh ? "隐私" : "Privacy" },
    { href: "/terms", label: isZh ? "条款" : "Terms" },
  ];

  const isActiveLink = (href: string) => {
    if (href === "/") {
      return normalizedPathname === "/";
    }

    if (href === "/sample") {
      return (
        normalizedPathname === "/sample" ||
        normalizedPathname.startsWith("/sample/")
      );
    }

    return normalizedPathname === href;
  };

  const pillClassName = (isActive: boolean) =>
    cx(
      "inline-flex min-h-11 items-center rounded-full border font-medium transition-all duration-200",
      isZh
        ? "px-4 py-2.5 text-[12px] tracking-[0.05em]"
        : "px-3.5 py-2 text-[11px] uppercase tracking-[0.18em]",
      tone === "dark" ? focusRingOnDark : focusRingOnLight,
      tone === "dark"
        ? isActive
          ? "border-white/30 bg-white text-[#020617] shadow-[0_14px_40px_rgba(255,255,255,0.12)]"
          : "border-white/10 bg-white/[0.04] text-white/62 hover:border-white/18 hover:bg-white/[0.08] hover:text-white"
        : isActive
          ? "border-[#2563eb]/14 bg-[#2563eb] text-white shadow-[0_14px_36px_rgba(37,99,235,0.24)]"
          : "border-black/6 bg-white/88 text-[#64748b] hover:border-[#2563eb]/16 hover:bg-white hover:text-[#0f172a] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]"
    );

  const linksMarkup = (
    <div className="flex flex-wrap items-center gap-2">
      {links.map((link) => (
        <Link
          key={link.href}
          href={buildLocalePath(locale, link.href)}
          aria-current={isActiveLink(link.href) ? "page" : undefined}
          className={pillClassName(isActiveLink(link.href))}
        >
          {link.label}
        </Link>
      ))}
    </div>
  );

  if (variant === "panel") {
    return (
      <nav
        aria-label={isZh ? "支持导航" : "Support navigation"}
        className={cx(
          "rounded-[1.8rem] border px-5 py-5 shadow-[0_22px_60px_rgba(15,23,42,0.08)] backdrop-blur",
          tone === "dark"
            ? "border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.04))]"
            : "border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(248,250,252,0.88))]",
          className
        )}
      >
        <p
          className={cx(
            isZh
              ? "text-[12px] font-medium tracking-[0.06em]"
              : "text-[11px] uppercase tracking-[0.22em]",
            tone === "dark" ? "text-white/52" : "text-[#64748b]"
          )}
        >
          {isZh ? "支持导航" : "Support navigation"}
        </p>
        <p
          className={cx(
            "mt-2 max-w-2xl text-sm leading-relaxed",
            tone === "dark" ? "text-white/64" : "text-[#475569]"
          )}
        >
          {isZh
            ? "快速跳转到核心公开页面，查看方法、示例内容与合规说明。"
            : "Jump between the core public pages for methodology, samples, and trust documentation."}
        </p>
        <div className="mt-4">{linksMarkup}</div>
      </nav>
    );
  }

  return (
    <nav
      aria-label={isZh ? "支持导航" : "Support navigation"}
      className={cx(
        "inline-flex max-w-full flex-wrap items-center gap-2 rounded-[1.6rem] border p-2 shadow-[0_18px_48px_rgba(15,23,42,0.08)] backdrop-blur",
        tone === "dark"
          ? "border-white/10 bg-white/[0.06]"
          : "border-white/70 bg-white/80",
        className
      )}
    >
      {linksMarkup}
    </nav>
  );
}
