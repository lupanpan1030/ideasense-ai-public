"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

export function SampleNotice() {
  const locale = useAppLocale();
  const messages = useAppMessages().sample.notice;
  return (
    <Card variant="soft" className="stack-sm">
      <CardHeader className="stack-sm">
        <div className="cluster">
          <Badge variant="info">{messages.badge}</Badge>
          <span className="text-muted">{messages.meta}</span>
        </div>
        <CardTitle>{messages.title}</CardTitle>
        <CardDescription>{messages.description}</CardDescription>
      </CardHeader>
      <CardFooter className="cluster">
        <Link className={buttonClassNames()} href={buildLocalePath(locale, "/register")}>
          {messages.createAccount}
        </Link>
        <Link
          className={buttonClassNames({ variant: "ghost" })}
          href={buildLocalePath(locale, "/login")}
        >
          {messages.signIn}
        </Link>
      </CardFooter>
    </Card>
  );
}
