import Link from "next/link";
import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import { Badge } from "@/components/ui/badge";
import { buttonClassNames } from "@/components/ui/button";
import type { AppLocale } from "@/lib/i18n/config";
import { buildLocalePath } from "@/lib/i18n/config";
import type { AppMessages } from "@/lib/i18n/messages";

type SampleReportHeroProps = {
  decisionBand: string;
  isZh: boolean;
  locale: AppLocale;
  messages: AppMessages["reportViewer"];
  projectId: string;
  projectTitle: string;
  riskCount: number;
  totalScore: string;
};

export function SampleReportHero({
  isZh,
  messages,
  projectId,
  projectTitle,
  decisionBand,
  totalScore,
  riskCount,
  locale,
}: SampleReportHeroProps) {
  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="overflow-hidden rounded-[2.6rem] border border-black/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(241,245,249,0.92))] p-4 shadow-[0_28px_90px_rgba(15,23,42,0.08)] md:p-5">
        <div className="rounded-[2.2rem] border border-black/6 bg-white/86 p-6 md:p-8">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)] lg:items-end">
            <div className="max-w-[760px]">
              <div className="inline-flex items-center rounded-full border border-[#2563eb]/12 bg-[#2563eb]/6 px-3 py-1.5 text-[12px] font-medium tracking-[0.03em] text-[#2563eb]">
                {messages.shell.sampleHero.eyebrow}
              </div>
              <h1
                className={[
                  "mt-5 font-semibold text-[#0f172a]",
                  isZh
                    ? "max-w-[11em] text-[clamp(2.25rem,4.4vw,3.8rem)] leading-[1.16] tracking-[-0.02em]"
                    : "max-w-[12ch] text-[clamp(2.6rem,5vw,4.6rem)] leading-[0.96] tracking-[-0.05em]",
                ].join(" ")}
              >
                {messages.shell.sampleHero.title}
              </h1>
              <p
                className={[
                  "mt-5 max-w-[42rem] text-[#475569]",
                  isZh
                    ? "text-[15px] leading-[1.9] md:text-[17px]"
                    : "text-base leading-relaxed md:text-lg",
                ].join(" ")}
              >
                {messages.shell.sampleHero.description}
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  className={buttonClassNames()}
                  href={buildLocalePath(locale, "/register")}
                >
                  {messages.shell.actions.createAccount}
                </Link>
                <Link
                  className={buttonClassNames({ variant: "secondary" })}
                  href={buildLocalePath(locale, "/sample")}
                >
                  {isZh ? "查看示例工作区" : "Explore Sample Workspace"}
                </Link>
                <Link
                  className={buttonClassNames({ variant: "ghost" })}
                  href={buildLocalePath(locale, "/login")}
                >
                  {messages.shell.actions.signIn}
                </Link>
              </div>
            </div>

            <div className="rounded-[2rem] border border-black/8 bg-[#f8fafc] p-5">
              <div className="flex items-start justify-between gap-4 border-b border-black/6 pb-4">
                <div>
                  <p className="text-[12px] font-medium tracking-[0.03em] text-[#2563eb]">
                    {messages.shell.sampleHero.readOnlyBadge}
                  </p>
                  <p className="mt-3 text-[22px] font-semibold leading-[1.28] tracking-[-0.018em] text-[#0f172a]">
                    {projectTitle}
                  </p>
                </div>
                <Badge variant="outline">{projectId}</Badge>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <SampleHeroStat
                  label={messages.shell.labels.decisionBand}
                  value={decisionBand}
                />
                <SampleHeroStat
                  label={messages.shell.labels.totalDvfScore}
                  value={totalScore}
                />
                <SampleHeroStat
                  label={messages.shell.labels.risksFlagged}
                  value={String(riskCount)}
                />
              </div>

              <div className="mt-5 rounded-[1.5rem] border border-black/6 bg-white px-4 py-4">
                <p className="text-[12px] font-medium tracking-[0.03em] text-[#2563eb]">
                  {messages.shell.title}
                </p>
                <p className="mt-3 text-[15px] leading-[1.82] text-[#475569]">
                  {messages.shell.sampleHero.note}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <MarketingSupportLinks isZh={isZh} variant="panel" className="mt-4" />
    </div>
  );
}

function SampleHeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.3rem] border border-black/6 bg-white px-4 py-4">
      <p className="text-[12px] font-medium tracking-[0.03em] text-[#64748b]">
        {label}
      </p>
      <p className="mt-3 text-[17px] font-medium leading-[1.35] tracking-[-0.012em] text-[#0f172a]">
        {value}
      </p>
    </div>
  );
}
