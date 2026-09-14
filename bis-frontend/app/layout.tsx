import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/app/components/ThemeProvider";
import { LanguageProvider } from "@/app/components/LanguageContext";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

export const metadata: Metadata = {
  title: {
    default: "BIS Knowledge Portal",
    template: "%s | BIS Knowledge Portal",
  },
  description:
    "Bureau of Indian Standards — AI-powered knowledge assistant for BIS standards, regulations, and laboratory finder.",
  keywords: ["BIS", "Bureau of Indian Standards", "standards", "regulations", "ISI", "India"],
  openGraph: {
    title: "BIS Knowledge Portal",
    description: "AI-powered assistant for BIS standards and regulations.",
    type: "website",
    locale: "en_IN",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          inter.variable,
          "min-h-screen bg-background font-sans antialiased"
        )}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <LanguageProvider>
            {children}
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
