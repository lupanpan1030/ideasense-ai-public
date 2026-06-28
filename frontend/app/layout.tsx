import type { Metadata } from "next";

import "./globals.css";
import { AppI18nProvider } from "@/lib/i18n/provider";
import { getRequestLocale } from "@/lib/i18n/request-locale";
import { SITE_NAME, SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: "Structured AI review for startup ideas before you build.",
  applicationName: SITE_NAME,
  openGraph: {
    siteName: SITE_NAME,
    type: "website",
  },
  twitter: {
    card: "summary",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const initialLocale = await getRequestLocale();

  return (
    <html lang={initialLocale} data-theme="light" data-locale={initialLocale}>
      <body className="app-root">
        <AppI18nProvider initialLocale={initialLocale}>
          {children}
        </AppI18nProvider>
      </body>
    </html>
  );
}
