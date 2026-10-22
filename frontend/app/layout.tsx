import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VeriHire",
  description: "Privacy-first hiring verification for candidates and employers.",
  icons: {
    icon: "https://res.cloudinary.com/f7ko7ayw/image/upload/v1788009964/VeriHire_Logo_BG2_b2ddm0.png",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[#070b10] text-[#edf3f8]">{children}</body>
    </html>
  );
}
