"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Leaf } from "lucide-react";
import { getBackendUrl } from "@/services/api";
import { LoginForm } from "@/components/login/LoginForm";
import { AuthFeedback } from "@/components/login/AuthFeedback";

/**
 * Login & Registration page for EcoPilot AI.
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

        <AuthFeedback errorMsg={errorMsg} successMsg={successMsg} />

        <div className="mt-4">
          <LoginForm
            isLogin={isLogin}
            email={email}
            setEmail={setEmail}
            password={password}
            setPassword={setPassword}
            fullName={fullName}
            setFullName={setFullName}
            loading={loading}
            onSubmit={handleSubmit}
          />
        </div>

        <div className="border-t border-slate-900 mt-6 pt-5 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setErrorMsg("");
              setSuccessMsg("");
            }}
            className="text-xs text-slate-400 hover:text-emerald-450 transition-colors cursor-pointer"
          >
            {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Log In"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
