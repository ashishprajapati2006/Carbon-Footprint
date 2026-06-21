"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Sparkles } from "lucide-react";

/** Props for the AuthFeedback component. */
interface AuthFeedbackProps {
  errorMsg: string;
  successMsg: string;
}

/**
 * AuthFeedback — Renders warning/error alerts or success confirmation prompts accessibly.
 */
export function AuthFeedback({ errorMsg, successMsg }: AuthFeedbackProps) {
  return (
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
  );
}
