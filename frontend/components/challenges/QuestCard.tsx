"use client";

import React from "react";
import { CheckCircle, Leaf, Car, Zap, Trash2 } from "lucide-react";

/** A single leaderboard challenge quest. */
interface EcoChallenge {
  id: string;
  quest_title: string;
  description: string;
  xp_yield: number;
  category: string;
  goal_amount: number;
  current_amount: number;
  status: "in_progress" | "completed" | "not_started" | "claimed";
}

/** Props for the QuestCard component. */
interface QuestCardProps {
  quest: EcoChallenge;
  onClaim: (id: string) => Promise<void>;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  food: Leaf,
  transport: Car,
  energy: Zap,
  waste: Trash2
};

const colorMap: Record<string, string> = {
  food: "text-emerald-500",
  transport: "text-blue-500",
  energy: "text-amber-500",
  waste: "text-slate-550"
};

const bgMap: Record<string, string> = {
  food: "bg-emerald-500/10",
  transport: "bg-blue-500/10",
  energy: "bg-amber-500/10",
  waste: "bg-slate-500/10"
};

/**
 * QuestCard — Displays a single sustainability challenge with a progress tracker and action button.
 */
export function QuestCard({ quest, onClaim }: QuestCardProps) {
  const IconComp = iconMap[quest.category] || Leaf;
  const iconColor = colorMap[quest.category] || "text-emerald-500";
  const iconBg = bgMap[quest.category] || "bg-emerald-500/10";
  const isFinished = quest.current_amount >= quest.goal_amount;
  const isClaimed = quest.status === "claimed";

  return (
    <div 
      className={`glass-panel rounded-2xl p-6 flex flex-col justify-between glass-panel-hover relative overflow-hidden ${
        isClaimed ? "border-emerald-500/20 bg-emerald-950/5" : ""
      }`}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className={`w-9 h-9 rounded-lg ${iconBg} flex items-center justify-center`}>
            <IconComp className={`w-4.5 h-4.5 ${iconColor}`} />
          </div>
          <span className="font-mono text-[10px] text-primary bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10 font-bold">
            +{quest.xp_yield} XP
          </span>
        </div>

        <div className="space-y-1">
          <h3 className="font-bold text-foreground text-sm flex items-center gap-1.5">
            {quest.quest_title}
            {isClaimed && <CheckCircle className="w-4 h-4 text-primary shrink-0" />}
          </h3>
          <p className="text-xs text-muted leading-relaxed">{quest.description}</p>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5 text-[10px]">
          <div className="flex items-center justify-between text-slate-500 font-bold">
            <span>Progress</span>
            <span>{quest.current_amount} / {quest.goal_amount}</span>
          </div>
          <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden">
            <div 
              className="h-full bg-slate-500 transition-all duration-300"
              style={{ width: `${Math.min((quest.current_amount / quest.goal_amount) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="pt-6">
        {isClaimed ? (
          <button 
            disabled 
            className="w-full py-2.5 rounded-lg border border-emerald-500/10 bg-emerald-950/10 text-emerald-500 font-bold text-xs"
          >
            Claimed
          </button>
        ) : isFinished ? (
          <button 
            onClick={() => onClaim(quest.id)}
            className="w-full py-2.5 rounded-lg text-white font-bold glow-btn text-xs cursor-pointer"
          >
            Claim XP Reward
          </button>
        ) : (
          <button 
            disabled
            className="w-full py-2.5 rounded-lg border border-slate-900 bg-slate-950/20 text-slate-500 font-bold text-xs"
          >
            In Progress
          </button>
        )}
      </div>
    </div>
  );
}
