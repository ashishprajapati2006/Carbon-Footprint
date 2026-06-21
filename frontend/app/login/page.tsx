"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Leaf, Mail, Lock, User, ArrowRight, ShieldAlert, Sparkles, LogIn } from "lucide-react";
import { getBackendUrl } from "@/services/api";

/**
 * Login & Registration page for EcoPilot AI.
 *
 * Provides unified authentication UI for new user registration and
 * returning user sign-in. On successful auth, stores JWT tokens and
 * redirects to the carbon dashboard. Password complexity is enforced
 * server-side and error messages are surfaced accessibly via role="alert".
 */

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMsg("Please fill out all required fields.");
      return;
    }
    if (!isLogin && !fullName.trim()) {
      setErrorMsg("Full name is required for registration.");
      return;
    }

    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const endpoint = isLogin ? "/auth/login" : "/auth/register";
      const payload = isLogin 
        ? { email, password }
        : { email, password, full_name: fullName, profile: { country: "US", household_size: 2, diet_preference: "vegetarian", has_car: true } };

      const res = await fetch(getBackendUrl(endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        let errorString = "Authentication request failed.";
        if (data && data.detail) {
          if (typeof data.detail === "string") {
            errorString = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorString = data.detail
              .map((err: any) => {
                const field = err.loc ? err.loc[err.loc.length - 1] : "";
                return field ? `${field}: ${err.msg}` : err.msg;
              })
              .join(", ");
          } else if (typeof data.detail === "object") {
            errorString = JSON.stringify(data.detail);
          }
        }
        throw new Error(errorString);
      }

      // Store tokens and metadata
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      localStorage.setItem("user", JSON.stringify({ email, full_name: data.full_name || fullName || "EcoPilot User" }));

      setSuccessMsg(isLogin ? "Welcome back! Redirecting..." : "Registration successful! Loading your dashboard...");
      
      setTimeout(() => {
        router.push("/dashboard");
      }, 1200);

    } catch (err: any) {
      setErrorMsg(err.message || "Something went wrong. Please check your inputs or backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-10 px-4">
      <div className="absolute inset-0 bg-gradient-to-tr from-emerald-950/20 via-slate-950 to-blue-950/20 -z-10" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md glass-panel p-8 rounded-3xl border border-slate-800/80 shadow-2xl relative overflow-hidden"
      >
        {/* Glow accents */}
        <div className="absolute -top-12 -right-12 w-32 h-32 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-32 h-32 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

        <div className="text-center space-y-2 mb-8">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-blue-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Leaf className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">
            {isLogin ? "Welcome to EcoPilot" : "Create Eco Account"}
          </h2>
          <p className="text-xs text-slate-400">
            {isLogin ? "Sign in to coordinate your path to Net Zero" : "Sign up and begin tracking your footprint today"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="popLayout">
            {!isLogin && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-1.5"
              >
                <label htmlFor="fullName-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Full Name</label>
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
            <label htmlFor="email-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Email Address</label>
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
            <label htmlFor="password-input" className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Password</label>
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

          {/* Feedback Messages */}
          <AnimatePresence>
            {errorMsg && (
              <motion.div 
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                role="alert"
                aria-live="assertive"
                className="p-3 bg-rose-950/30 border border-rose-500/30 text-rose-350 text-[11px] rounded-xl flex items-center gap-2"
              >
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-500" />
                <span>{errorMsg}</span>
              </motion.div>
            )}

            {successMsg && (
              <motion.div 
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="p-3 bg-emerald-950/30 border border-emerald-500/30 text-emerald-350 text-[11px] rounded-xl flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4 shrink-0 text-emerald-400 animate-pulse" />
                <span>{successMsg}</span>
              </motion.div>
            )}
          </AnimatePresence>

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

        <div className="border-t border-slate-900 mt-6 pt-5 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setErrorMsg("");
              setSuccessMsg("");
            }}
            className="text-xs text-slate-400 hover:text-emerald-450 transition-colors"
          >
            {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Log In"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
