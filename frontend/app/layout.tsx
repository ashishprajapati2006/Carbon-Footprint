"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { 
  LayoutGrid, Leaf, Compass, Bot, FileText, Zap, BarChart2, Award, Sun, Moon, Menu, X, Globe,
  LogIn, LogOut, User as UserIcon
} from "lucide-react";
import { getAuthUser, logoutUser } from "@/services/api";
import "./globals.css";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    // Sync theme on mount
    const savedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.className = savedTheme;
    } else {
      document.documentElement.className = "dark";
    }
  }, []);

  useEffect(() => {
    // Sync user session details
    setUser(getAuthUser());
  }, [pathname]);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("theme", nextTheme);
    document.documentElement.className = nextTheme;
  };

  const navItems = [
    { name: "Landing Page", href: "/", icon: Globe },
    { name: "Dashboard", href: "/dashboard", icon: LayoutGrid },
    { name: "Calculator", href: "/calculator", icon: Leaf },
    { name: "AI Coach", href: "/coach", icon: Bot },
    { name: "Carbon Twin", href: "/twin", icon: Compass },
    { name: "Bill Analyzer", href: "/bills", icon: Zap },
    { name: "EcoVision Scanner", href: "/rooms", icon: FileText },
    { name: "Challenges", href: "/challenges", icon: Award },
    { name: "Leaderboard", href: "/leaderboard", icon: Award }, // Can customize icons
  ];

  return (
    <html lang="en" className={theme}>
      <body className="antialiased min-h-screen flex text-slate-100 dark:text-slate-100 bg-background text-sm">
        
        {/* Toggle Theme Button (Floating on Mobile) */}
        <div className="fixed bottom-6 right-6 z-50 md:bottom-auto md:top-4 md:right-8">
          <button 
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="w-11 h-11 rounded-full flex items-center justify-center border border-emerald-950/20 dark:border-emerald-500/20 bg-slate-900/80 text-white shadow-xl hover:scale-105 transition-all cursor-pointer"
          >
            {theme === "dark" ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-blue-500" />}
          </button>
        </div>

        {/* Mobile Header Nav bar */}
        <div className="md:hidden fixed top-0 left-0 w-full z-40 px-4 py-3 border-b border-border bg-background/80 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-gradient-to-tr from-emerald-500 to-blue-600 flex items-center justify-center">
              <span className="font-bold text-white text-xs">E</span>
            </div>
            <span className="font-bold text-md tracking-tight text-foreground">EcoPilot AI</span>
          </div>
          
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle Navigation Sidebar"
            className="p-1.5 border border-border rounded text-foreground hover:bg-emerald-950/10 transition-colors cursor-pointer"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation Sidebar Panel */}
        <aside 
          className={`fixed md:sticky top-0 left-0 z-40 h-screen w-60 border-r border-border bg-slate-950/40 md:bg-slate-950/15 backdrop-blur-xl flex flex-col justify-between py-6 px-4 transition-transform md:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="space-y-6">
            {/* Logo */}
            <div className="flex items-center gap-2.5 px-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-blue-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <span className="font-bold text-white text-base">E</span>
              </div>
              <div>
                <span className="font-bold text-base text-foreground tracking-tight block">EcoPilot</span>
                <span className="text-[10px] text-emerald-450 uppercase tracking-widest font-bold block -mt-1">AI PLATFORM</span>
              </div>
            </div>

            {/* Navigation links */}
            <nav className="space-y-1" aria-label="Main Navigation">
              {navItems.map((item, idx) => {
                const IconComp = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link 
                    key={idx}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-semibold transition-all group ${
                      isActive 
                        ? "bg-emerald-600/10 text-emerald-400 border-l-2 border-emerald-500 pl-2.5" 
                        : "text-muted hover:text-foreground hover:bg-slate-800/10"
                    }`}
                  >
                    <IconComp className={`w-4 h-4 shrink-0 transition-colors ${isActive ? "text-emerald-400" : "text-slate-500 group-hover:text-emerald-400"}`} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer Info */}
          {user ? (
            <div className="border-t border-border pt-4 mt-auto space-y-3">
              <div className="flex items-center justify-between bg-slate-900/40 border border-slate-800/80 rounded-xl p-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 flex items-center justify-center shrink-0">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <span className="font-semibold text-xs text-white block truncate leading-tight">{user.full_name || "EcoPilot User"}</span>
                    <span className="text-[9px] text-slate-500 block truncate mt-0.5">{user.email}</span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    logoutUser();
                    setUser(null);
                    router.push("/login");
                  }}
                  className="p-1 rounded-lg hover:bg-slate-850 text-slate-400 hover:text-rose-450 transition-colors cursor-pointer shrink-0"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="text-[10px] text-slate-550 font-semibold tracking-wide text-center">
                <span>EcoPilot Platform v1.2</span>
              </div>
            </div>
          ) : (
            <div className="border-t border-border pt-4 mt-auto space-y-3">
              <Link
                href="/login"
                className="flex items-center justify-center gap-2 bg-emerald-950/40 hover:bg-emerald-950/80 border border-emerald-500/20 hover:border-emerald-500/40 text-emerald-400 font-bold py-2 px-3 rounded-xl text-xs transition-all cursor-pointer w-full text-center"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Authenticate Session</span>
              </Link>
              <div className="text-[10px] text-slate-550 font-semibold tracking-wide text-center">
                <span>EcoPilot Platform v1.2</span>
              </div>
            </div>
          )}
        </aside>

        {/* Content Wrapper */}
        <div className="flex-1 min-h-screen flex flex-col pt-16 md:pt-0">
          <main className="flex-grow w-full max-w-6xl mx-auto px-4 py-8 md:px-8">
            {children}
          </main>
          
          <footer className="w-full text-center py-4 text-[10px] text-slate-500 font-semibold border-t border-border">
            EcoPilot AI © 2026. Responsive Accessibility Design.
          </footer>
        </div>

      </body>
    </html>
  );
}
