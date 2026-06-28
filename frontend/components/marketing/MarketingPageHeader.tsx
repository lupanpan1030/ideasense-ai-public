"use client";

import Link from "next/link";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";

type MarketingPageHeaderProps = {
  isZh: boolean;
};

export function MarketingPageHeader({
  isZh,
}: MarketingPageHeaderProps) {
  const locale = useAppLocale();

  return (
    <header className="rounded-[2rem] border border-white/70 bg-white/78 px-4 py-4 shadow-[0_20px_46px_rgba(15,23,42,0.08)] backdrop-blur-xl">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href={buildLocalePath(locale, "/")}
          className={[
            "inline-flex shrink-0 items-center rounded-full px-4 py-2 text-[17px] font-semibold tracking-[-0.03em] text-[#0f172a] transition hover:bg-white",
            focusRingOnLight,
          ].join(" ")}
        >
          <span>IdeaSense</span>
          <span className="ml-1 text-[#2563eb]">AI</span>
        </Link>

        <div className="ml-auto flex items-center gap-2 md:hidden">
          <LanguageSwitcher compact />
        </div>

        <div className="hidden flex-1 justify-center md:flex">
          <MarketingSupportLinks isZh={isZh} variant="dock" />
        </div>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <LanguageSwitcher compact />
        </div>
      </div>

      <div className="mt-3 md:hidden">
        <MarketingSupportLinks isZh={isZh} variant="dock" className="w-full" />
      </div>
    </header>
  );
}
