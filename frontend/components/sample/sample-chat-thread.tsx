"use client";

import { useRef } from "react";
import Link from "next/link";
import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import { buttonClassNames } from "@/components/ui/button";
import { ChatThreadMessages } from "@/features/chat/chat-thread-messages";
import type { ChatMessage } from "@/features/chat/chat-state";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type SampleChatThreadProps = {
  messages: ChatMessage[];
  projectTitle?: string | null;
};

export function SampleChatThread({
  messages,
  projectTitle,
}: SampleChatThreadProps) {
  const sampleMessages = useAppMessages().sample.thread;
  const locale = useAppLocale();
  const isZh = locale === "zh";
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  return (
    <div className="chat-thread">
      <ChatThreadMessages
        messages={messages}
        isLoading={false}
        isLoadingMore={false}
        historyError={null}
        streamError={null}
        onRetryHistory={() => {}}
        scrollContainerRef={scrollContainerRef}
        onScroll={() => {}}
      />

      <div className="composer" aria-label={sampleMessages.ariaLabel}>
        <div className="composer__row flex-col items-start gap-2">
          <span className="text-sm text-muted-foreground">
            {projectTitle
              ? sampleMessages.readOnlyWithProject.replace(
                  "{projectTitle}",
                  projectTitle
                )
              : sampleMessages.readOnlyDefault}
          </span>
          <div className="cluster">
            <Link
              className={buttonClassNames()}
              href={buildLocalePath(locale, "/register")}
            >
              {sampleMessages.createAccount}
            </Link>
            <Link
              className={buttonClassNames({ variant: "ghost" })}
              href={buildLocalePath(locale, "/login")}
            >
              {sampleMessages.signIn}
            </Link>
          </div>

          <MarketingSupportLinks isZh={isZh} variant="panel" className="w-full" />
        </div>
      </div>
    </div>
  );
}
