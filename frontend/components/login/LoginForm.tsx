"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { User, Mail, Lock, ArrowRight } from "lucide-react";

/** Props for the LoginForm component. */
interface LoginFormProps {
  isLogin: boolean;
  email: string;
  setEmail: (val: string) => void;
  password: string;
  setPassword: (val: string) => void;
  fullName: string;
  setFullName: (val: string) => void;
  loading: boolean;
  onSubmit: (e: React.FormEvent) => Promise<void>;
}

/**
 * LoginForm — Renders the input fields and submit button for user login and registration.
 */
export function LoginForm({
  isLogin,
  email,
  setEmail,
  password,
  setPassword,
  fullName,
  setFullName,
  loading,
  onSubmit
}: LoginFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <AnimatePresence mode="popLayout">
        {!isLogin && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-1.5"
          >
            <label htmlFor="fullName-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Full Name
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-500">
                <User className="w-4 h-4" />
              </span>
              <input
                id="fullName-input"
                type="text"
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-slate-950/70 border border-slate-800 focus:border-emerald-500/80 rounded-xl py-3 pl-10 pr-4 text-xs text-white focus:outline-none transition-colors"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-1.5">
        <label htmlFor="email-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
          Email Address
        </label>
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-500">
            <Mail className="w-4 h-4" />
          </span>
          <input
            id="email-input"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full bg-slate-950/70 border border-slate-800 focus:border-emerald-500/80 rounded-xl py-3 pl-10 pr-4 text-xs text-white focus:outline-none transition-colors"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <label htmlFor="password-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
          Password
        </label>
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-500">
            <Lock className="w-4 h-4" />
          </span>
          <input
            id="password-input"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            aria-describedby={!isLogin ? "password-hint" : undefined}
            className="w-full bg-slate-950/70 border border-slate-800 focus:border-emerald-500/80 rounded-xl py-3 pl-10 pr-4 text-xs text-white focus:outline-none transition-colors"
          />
        </div>
        {!isLogin && (
          <p id="password-hint" className="text-[10px] text-slate-500 mt-1">
            Must be 8+ characters with at least one uppercase letter, lowercase letter, and number.
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-850 text-white py-3.5 px-4 rounded-xl text-xs font-bold transition-all shadow-lg shadow-emerald-500/10 cursor-pointer flex items-center justify-center gap-2 mt-6"
      >
        {loading ? (
          <div className="w-4 h-4 border-2 border-t-white border-r-transparent rounded-full animate-spin" />
        ) : (
          <>
            <span>{isLogin ? "Authenticate Session" : "Create Eco Account"}</span>
            <ArrowRight className="w-4 h-4" />
          </>
        )}
      </button>
    </form>
  );
}
