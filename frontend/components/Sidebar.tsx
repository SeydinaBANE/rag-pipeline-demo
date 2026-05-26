"use client";

import { BarChart2, FileText, MessageSquare, ThumbsUp } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const NAV = [
  { href: "/chat", icon: MessageSquare, label: "Chat" },
  { href: "/documents", icon: FileText, label: "Documents" },
  { href: "/analytics", icon: BarChart2, label: "Analytics" },
  { href: "/feedback", icon: ThumbsUp, label: "Feedback" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken(localStorage.getItem("rag_token") ?? "");
  }, []);

  const handleTokenChange = (value: string) => {
    setToken(value);
    localStorage.setItem("rag_token", value);
  };

  return (
    <aside className="w-60 bg-gray-900 flex flex-col h-screen shrink-0">
      <div className="px-5 py-5 border-b border-gray-700/60">
        <span className="text-white font-semibold tracking-tight">RAG Pipeline</span>
        <p className="text-gray-500 text-xs mt-0.5">local dev · v0.1.0</p>
      </div>

      <nav className="flex-1 px-3 py-3 space-y-0.5">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 pb-5 pt-3 border-t border-gray-700/60">
        <p className="text-gray-500 text-xs font-medium uppercase tracking-wider mb-1.5">
          JWT Token
        </p>
        <input
          type="password"
          value={token}
          onChange={(e) => handleTokenChange(e.target.value)}
          placeholder="Paste your JWT…"
          className="w-full bg-gray-800 border border-gray-700 rounded-md px-2.5 py-1.5 text-gray-300 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-gray-600"
        />
        {token && (
          <p className="text-green-400 text-xs mt-1">✓ Token set</p>
        )}
      </div>
    </aside>
  );
}
