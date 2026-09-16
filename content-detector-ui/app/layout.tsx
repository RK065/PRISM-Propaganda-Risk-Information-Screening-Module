import React from "react";
import Link from "next/link";
import { 
  LayoutDashboard, 
  Search, 
  HelpCircle, 
  History, 
  BarChart3, 
  Settings, 
  Bell, 
  User, 
  ShieldAlert, 
  CheckSquare
} from "lucide-react";
import "./globals.css";

export const metadata = {
  title: "PRISM — Propaganda Recognition, Intelligence & Source Monitoring",
  description: "Detect manipulative narratives and verify claims with RAG intelligence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-background text-primaryText min-h-screen flex">
        {/* Sidebar */}
        <aside className="w-64 bg-card border-r border-border flex flex-col fixed h-full z-10">
          {/* Logo / Header */}
          <div className="p-6 border-b border-border flex items-center gap-3">
            <svg viewBox="0 0 24 24" className="w-8 h-8 text-primaryText" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Incoming Ray */}
              <path d="M2 15L9 11.5" stroke="#94A3B8" strokeWidth={1.5} strokeLinecap="round"/>
              {/* Prism Triangle */}
              <polygon points="12 5 6 17 18 17" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round"/>
              {/* Outgoing Beams (Spectrum) */}
              <path d="M15 11.5L22 8" stroke="#FB7185" strokeWidth={1.2} strokeLinecap="round"/>
              <path d="M15 12L22 12" stroke="#FBBF24" strokeWidth={1.2} strokeLinecap="round"/>
              <path d="M15 12.5L22 16" stroke="#2563eb" strokeWidth={1.2} strokeLinecap="round"/>
            </svg>
            <div>
              <h1 className="font-syncopate font-bold text-xs leading-tight text-primaryText tracking-[0.1em]">PRISM</h1>
              <p className="text-[10px] text-secondaryText tracking-widest font-mono">SYSTEM</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 px-4 py-6 space-y-1">
            <Link href="/" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <LayoutDashboard size={18} />
              Landing Page
            </Link>
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <LayoutDashboard size={18} />
              Dashboard
            </Link>
            <Link href="/analyzer" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <ShieldAlert size={18} />
              Content Analyzer
            </Link>
            <Link href="/fact-check" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <HelpCircle size={18} />
              Fact Verification
            </Link>
            <Link href="/review" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <CheckSquare size={18} />
              Human Review Queue
            </Link>
            <Link href="/analytics" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <BarChart3 size={18} />
              Analytics
            </Link>
          </nav>

          {/* User Settings Footer */}
          <div className="p-4 border-t border-border">
            <Link href="/settings" className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-secondaryText hover:text-primaryText hover:bg-slate-800 transition-colors">
              <Settings size={18} />
              Settings
            </Link>
          </div>
        </aside>

        {/* Main Workspace Frame */}
        <div className="flex-1 pl-64 flex flex-col min-h-screen">
          {/* Top Header Navigation Bar */}
          <header className="h-16 border-b border-border bg-slate-900/50 backdrop-blur px-8 flex items-center justify-between sticky top-0 z-20">
            <div className="flex items-center gap-3 bg-slate-800/80 px-4 py-1.5 rounded-lg border border-border w-96">
              <Search size={16} className="text-secondaryText" />
              <input 
                type="text" 
                placeholder="Search analysis history..." 
                className="bg-transparent border-none text-sm text-primaryText placeholder-secondaryText outline-none w-full"
              />
            </div>

            <div className="flex items-center gap-4">
              <button className="p-2 text-secondaryText hover:text-primaryText relative hover:bg-slate-800 rounded-full transition-colors">
                <Bell size={18} />
                <span className="absolute w-2 h-2 bg-danger rounded-full top-1.5 right-1.5 border border-slate-900"></span>
              </button>
              <div className="w-px h-6 bg-border"></div>
              <button className="flex items-center gap-2 px-3 py-1 hover:bg-slate-800 rounded-lg transition-colors">
                <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-sm font-semibold text-primaryText">
                  A
                </div>
                <span className="text-sm font-medium text-secondaryText">Analyst</span>
              </button>
            </div>
          </header>

          {/* Children Pages */}
          <main className="flex-1 p-8 bg-background">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
