import type { ReactNode } from "react";
import Link from "next/link";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import {
  type ActiveSectionId,
  type HomeContent,
  type SectionId,
  cx,
  focusRingOnLight,
} from "./home-page-utils";

type MarketingHeaderProps = {
  activeSection: ActiveSectionId;
  content: HomeContent;
  onNavigate: (sectionId: SectionId) => void;
  onScrollTop: () => void;
};

export function MarketingHeader({
  activeSection,
  content,
  onNavigate,
  onScrollTop,
}: MarketingHeaderProps) {
  const locale = useAppLocale();

  return (
    <header className="sticky top-4 z-50 px-4">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-full border border-white/70 bg-white/78 px-3 py-2 shadow-[0_20px_46px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onScrollTop}
              className={cx(
                "inline-flex shrink-0 items-center rounded-full px-4 py-2 text-[17px] font-semibold tracking-[-0.03em] text-[#0f172a] transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30",
                activeSection === "hero" && "bg-white shadow-[0_10px_24px_rgba(15,23,42,0.08)]"
              )}
            >
              <span>IdeaSense</span>
              <span className="ml-1 text-[#2563eb]">AI</span>
            </button>

            <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
              <HeaderNavButton
                active={activeSection === "features"}
                onClick={() => onNavigate("features")}
              >
                {content.nav.features}
              </HeaderNavButton>
              <HeaderNavButton
                active={activeSection === "process"}
                onClick={() => onNavigate("process")}
              >
                {content.nav.process}
              </HeaderNavButton>
              <HeaderNavButton
                active={activeSection === "faq"}
                onClick={() => onNavigate("faq")}
              >
                {content.nav.faq}
              </HeaderNavButton>
              <HeaderNavButton
                active={activeSection === "team"}
                onClick={() => onNavigate("team")}
              >
                {content.nav.team}
              </HeaderNavButton>
            </nav>

            <div className="ml-auto flex items-center gap-2">
              <LanguageSwitcher compact className="hidden md:flex" />
              <Link
                href={buildLocalePath(locale, "/login")}
                className={cx(
                  "hidden rounded-full border border-black/8 px-4 py-2 text-sm text-[#334155] transition hover:bg-white md:inline-flex",
                  focusRingOnLight
                )}
              >
                {content.nav.login}
              </Link>
              <Link
                href={buildLocalePath(locale, "/register")}
                className={cx(
                  "inline-flex items-center rounded-full bg-[#0f172a] px-4 py-2 text-sm text-white transition hover:bg-[#020617]",
                  focusRingOnLight
                )}
              >
                {content.nav.register}
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-2 flex gap-2 overflow-x-auto px-1 pb-1 md:hidden">
          <HeaderNavButton
            active={activeSection === "features"}
            onClick={() => onNavigate("features")}
          >
            {content.nav.features}
          </HeaderNavButton>
          <HeaderNavButton
            active={activeSection === "process"}
            onClick={() => onNavigate("process")}
          >
            {content.nav.process}
          </HeaderNavButton>
          <HeaderNavButton
            active={activeSection === "faq"}
            onClick={() => onNavigate("faq")}
          >
            {content.nav.faq}
          </HeaderNavButton>
          <HeaderNavButton
            active={activeSection === "team"}
            onClick={() => onNavigate("team")}
          >
            {content.nav.team}
          </HeaderNavButton>
        </div>
      </div>
    </header>
  );
}

function HeaderNavButton({
  active = false,
  children,
  onClick,
}: {
  active?: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "cursor-pointer rounded-full px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30",
        active
          ? "bg-white text-[#0f172a] shadow-[0_10px_24px_rgba(15,23,42,0.08)]"
          : "text-[#475569] hover:bg-white hover:text-[#0f172a]"
      )}
    >
      {children}
    </button>
  );
}
