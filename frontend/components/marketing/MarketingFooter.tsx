import Link from "next/link";

import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import {
  SITE_CONTACT_EMAIL,
  SITE_NAME,
  SITE_OPERATOR_LABEL,
  SITE_STATUS_LABEL,
  formatSiteCopyright,
} from "@/lib/site";

const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

type MarketingFooterProps = {
  isZh: boolean;
  className?: string;
};

export function MarketingFooter({
  isZh,
  className,
}: MarketingFooterProps) {
  const locale = isZh ? "zh" : "en";

  return (
    <footer className={cx("mt-16", className)}>
      <div className="rounded-[2rem] border border-black/6 bg-white/72 px-5 py-5 shadow-[0_20px_48px_rgba(15,23,42,0.05)] backdrop-blur md:px-6 md:py-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold tracking-[-0.02em] text-[#0f172a]">
                {SITE_NAME}
              </p>
              <span className="rounded-full border border-[#2563eb]/12 bg-[#eff6ff] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[#2563eb]">
                {SITE_STATUS_LABEL[locale]}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[#475569]">
              {SITE_OPERATOR_LABEL[locale]}
            </p>
          </div>

          <div className="lg:max-w-[28rem] lg:text-right">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[#64748b]">
              {isZh ? "公开页面" : "Public pages"}
            </p>
            <MarketingSupportLinks
              isZh={isZh}
              variant="dock"
              className="mt-3 border-black/6 bg-white/84 p-1.5 shadow-none lg:ml-auto"
            />
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-2 border-t border-black/6 pt-4 text-xs text-[#64748b] md:flex-row md:items-center md:justify-between">
          <p>
            {isZh ? "联系邮箱：" : "Contact:"}{" "}
            <Link
              href={`mailto:${SITE_CONTACT_EMAIL}`}
              className="font-medium text-[#334155] transition hover:text-[#0f172a] hover:underline hover:underline-offset-4"
            >
              {SITE_CONTACT_EMAIL}
            </Link>
          </p>
          <p>{formatSiteCopyright(new Date().getFullYear(), locale)}</p>
        </div>
      </div>
    </footer>
  );
}
