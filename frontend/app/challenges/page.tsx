"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Award, CheckCircle, Zap, Car, Leaf, Trash2, ArrowRight } from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";

export default function Challenges() {
  const [userXp, setUserXp] = useState(380);
  const [quests, setQuests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const initialQuests = [
    { id: "q1", quest_title: "Meatless Commute", description: "Eat vegetarian or vegan meals for 3 consecutive days.", xp_yield: 120, category: "food", goal_amount: 3, current_amount: 2, status: "in_progress" },
    { id: "q2", quest_title: "Transit Traveler", description: "Swap driving single commutes for rail or bus travel.", xp_yield: 150, category: "transport", goal_amount: 1, current_amount: 0, status: "in_progress" },
    { id: "q3", quest_title: "Standby Shutdown", description: "Audit and unplug 5 idle phantom electrical loads.", xp_yield: 60, category: "energy", goal_amount: 5, current_amount: 5, status: "completed" },
    { id: "q4", quest_title: "Refuse Restraint", description: "Keep household waste below 5kg this week.", xp_yield: 80, category: "waste", goal_amount: 1, current_amount: 1, status: "completed" }
  ];

  const iconMap: { [key: string]: any } = {
    food: Leaf,
    transport: Car,
    energy: Zap,
    waste: Trash2
  };

  const colorMap: { [key: string]: string } = {
    food: "text-emerald-500",
    transport: "text-blue-500",
    energy: "text-amber-500",
    waste: "text-slate-550"
  };

  const bgMap: { [key: string]: string } = {
    food: "bg-emerald-500/10",
    transport: "bg-blue-500/10",
    energy: "bg-amber-500/10",
    waste: "bg-slate-500/10"
  };

  const fetchGamificationData = async () => {
    try {
      const statsRes = await apiFetch(getBackendUrl("/gamification/stats"));
      if (statsRes.ok) {
        const stats = await statsRes.json();
        setUserXp(stats.points);
      }
      
      const questsRes = await apiFetch(getBackendUrl("/gamification/challenges"));
      if (questsRes.ok) {
        const questsData = await questsRes.json();
        setQuests(questsData);
      } else {
        throw new Error("Failed to fetch quests");
      }
    } catch (err) {
      console.warn("Backend offline. Loading default mock challenges.");
      setQuests(initialQuests);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGamificationData();
  }, []);

  const handleClaim = async (id: string) => {
    try {
      const res = await apiFetch(getBackendUrl(`/gamification/challenges/${id}/claim`), {
        method: "POST"
      });
      if (res.ok) {
        await fetchGamificationData();
      } else {
        throw new Error("Failed to claim reward");
      }
    } catch (err) {
      console.warn("Backend offline. Claiming locally for demo.");
      setQuests(prev => prev.map(q => q.id === id ? { ...q, status: "claimed" } : q));
      setUserXp(prev => prev + 100);
    }
  };

  const currentLevel = Math.floor(userXp / 200) + 1;
  const xpInLevel = userXp % 200;

  return (
    <div className="space-y-10">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Eco Challenges</h1>
          <p className="text-muted text-xs mt-1.5">Participate in sustainability tasks, log progress, and claim ecological XP rewards.</p>
        </div>

        {/* User Level Indicator */}
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
            <span className="text-[9px] text-slate-550 block font-semibold">{xpInLevel} / 200 XP to Level Up</span>
          </div>
        </div>
      </div>

      {/* Challenges Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs">Retrieving active challenges...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {quests.map((q) => {
            const IconComp = iconMap[q.category] || Leaf;
            const iconColor = colorMap[q.category] || "text-emerald-500";
            const iconBg = bgMap[q.category] || "bg-emerald-500/10";
            const isFinished = q.current_amount >= q.goal_amount;
            const isClaimed = q.status === "claimed";
            
            return (
              <div 
                key={q.id}
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
                      +{q.xp_yield} XP
                    </span>
                  </div>

                  <div className="space-y-1">
                    <h3 className="font-bold text-foreground text-sm flex items-center gap-1.5">
                      {q.quest_title}
                      {isClaimed && <CheckCircle className="w-4 h-4 text-primary shrink-0" />}
                    </h3>
                    <p className="text-xs text-muted leading-relaxed">{q.description}</p>
                  </div>

                  {/* Progress bar */}
                  <div className="space-y-1.5 text-[10px]">
                    <div className="flex items-center justify-between text-slate-500 font-bold">
                      <span>Progress</span>
                      <span>{q.current_amount} / {q.goal_amount}</span>
                    </div>
                    <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-slate-500 transition-all duration-300"
                        style={{ width: `${Math.min((q.current_amount / q.goal_amount) * 100, 100)}%` }}
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
                      onClick={() => handleClaim(q.id)}
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
          })}
        </div>
      )}

    </div>
  );
}
