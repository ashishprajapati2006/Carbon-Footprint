"use client";

import React from "react";
import { Award } from "lucide-react";

/** Props for the LevelIndicator component. */
interface LevelIndicatorProps {
  /** The total experience points (XP) of the user. */
  userXp: number;
}

/**
 * LevelIndicator — Displays the user's gamified sustainability level and XP progress.
 */
export function LevelIndicator({ userXp }: LevelIndicatorProps) {
  const currentLevel = Math.floor(userXp / 200) + 1;
  const xpInLevel = userXp % 200;

  return (
    <div className="glass-panel rounded-2xl p-4 flex items-center gap-4 bg-gradient-to-r from-emerald-950/10 to-transparent self-start w-full sm:w-auto">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-blue-600 flex items-center justify-center shadow-lg">
        <Award className="w-5 h-5 text-white animate-pulse" />
      </div>
      <div className="space-y-1 text-xs">
        <span className="font-bold text-foreground">Level {currentLevel} Eco-Pioneer</span>
        <div className="w-32 h-1.5 bg-slate-900 border border-slate-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-emerald-500 transition-all duration-500" 
            style={{ width: `${(xpInLevel / 200) * 100}%` }}
          />
        </div>
        <span className="text-[9px] text-slate-550 block font-semibold">
          {xpInLevel} / 200 XP to Level Up
        </span>
      </div>
    </div>
  );
}
