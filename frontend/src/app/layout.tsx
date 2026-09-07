import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppQueryProvider } from "@/lib/query-client";
import { SiteHeader } from "@/components/layout/site-header";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ACME Compensation",
  description:
    "Salary management and compensation intelligence for ACME's HR team.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-muted/30">
        <AppQueryProvider>
          <TooltipProvider delay={200}>
            <SiteHeader />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
              {children}
            </main>
            <Toaster richColors closeButton />
          </TooltipProvider>
        </AppQueryProvider>
      </body>
    </html>
  );
}
