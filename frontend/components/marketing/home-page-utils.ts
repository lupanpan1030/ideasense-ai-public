import { useEffect, useState } from "react";
import {
  resolveMarketingContent,
  type MarketingContent,
} from "@/components/marketing/content";
import { useAppLocale } from "@/lib/i18n/provider";

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
export const MARKETING_SECTION_IDS = ["features", "process", "faq", "team"] as const;

export const MARKETING_ASSETS = {
  heroPoster: "/marketing/welcome/hero/ideasense-dogfooding-demo-poster.png",
  heroVideoWebm: "/marketing/welcome/hero/ideasense-dogfooding-demo.webm",
  heroVideoMp4: "/marketing/welcome/hero/ideasense-dogfooding-demo.mp4",
  reportCover: "/marketing/welcome/hero/ideasense-dogfooding-demo-poster.png",
  reportDetail: "/marketing/welcome/hero/ideasense-dogfooding-report-detail.png",
  founderPortrait: "/marketing/welcome/team/founder-portrait.jpg",
};

export type HomeContent = MarketingContent["home"];
export type MethodologyContent = MarketingContent["methodology"];
export type SectionId = (typeof MARKETING_SECTION_IDS)[number];
export type ActiveSectionId = "hero" | SectionId;

export const useMarketingPageContent = (): MarketingContent =>
  resolveMarketingContent(useAppLocale());

export const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";
export const focusRingOnDark =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#081223]";

export function useActiveMarketingSection(sectionIds: SectionId[]) {
  const [activeSection, setActiveSection] = useState<ActiveSectionId>("hero");

  useEffect(() => {
    const sections = sectionIds
      .map((id) => document.getElementById(id))
      .filter((section): section is HTMLElement => section !== null);

    if (!sections.length) {
      return;
    }

    const handleScroll = () => {
      if (window.scrollY < window.innerHeight * 0.35) {
        setActiveSection("hero");
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visibleEntries[0]) {
          setActiveSection(visibleEntries[0].target.id as SectionId);
          return;
        }

        handleScroll();
      },
      {
        rootMargin: "-20% 0px -55% 0px",
        threshold: [0.16, 0.3, 0.45, 0.6],
      }
    );

    sections.forEach((section) => observer.observe(section));
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", handleScroll);
    };
  }, [sectionIds]);

  return activeSection;
}
