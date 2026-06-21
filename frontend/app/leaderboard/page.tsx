"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Award, Trophy, Users, ShieldCheck, ChevronUp, Globe, Calendar, Zap } from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";

export default function Leaderboard() {
  const [activeTab, setActiveTab] = useState("global");
  const [rankings, setRankings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const mockWeeklyRankings = [
    { rank: 1, name: "Marcus Aurelius", level: "Carbon Neutral Hero", points: 80, isMe: false },
    { rank: 2, name: "Clara Schumann", level: "Eco Warrior", points: 70, isMe: false },
    { rank: 3, name: "EcoPilot Demo User", level: "Level 1 Eco-Pioneer", points: 50, isMe: true },
    { rank: 4, name: "Ada Lovelace", level: "Eco Warrior", points: 30, isMe: false }
  ];

  const mockMonthlyRankings = [
    { rank: 1, name: "Marcus Aurelius", level: "Carbon Neutral Hero", points: 280, isMe: false },
    { rank: 2, name: "EcoPilot Demo User", level: "Level 1 Eco-Pioneer", points: 250, isMe: true },
    { rank: 3, name: "Clara Schumann", level: "Eco Warrior", points: 220, isMe: false },
    { rank: 4, name: "Ada Lovelace", level: "Eco Warrior", points: 190, isMe: false }
  ];

  const mockGlobalRankings = [
    { rank: 1, name: "Marcus Aurelius", level: "Carbon Neutral Hero", points: 1800, isMe: false },
    { rank: 2, name: "Clara Schumann", level: "Eco Warrior", points: 1240, isMe: false },
    { rank: 3, name: "Ada Lovelace", level: "Eco Warrior", points: 1090, isMe: false },
    { rank: 4, name: "EcoPilot Demo User", level: "Level 1 Eco-Pioneer", points: 380, isMe: true }
  ];

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(getBackendUrl(`/gamification/leaderboard?period=${activeTab}`));
      if (res.ok) {
        const data = await res.json();
        setRankings(data);
      } else {
        throw new Error("Failed to fetch");
      }
    } catch (err) {
      console.warn("Backend offline, falling back to mock rankings.");
      if (activeTab === "weekly") {
        setRankings(mockWeeklyRankings);
      } else if (activeTab === "monthly") {
        setRankings(mockMonthlyRankings);
      } else {
        setRankings(mockGlobalRankings);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, [activeTab]);

  return (
    <div className="space-y-10">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Eco Leaderboard</h1>
        <p className="text-muted text-xs mt-1.5">Compare ecological points and weekly, monthly, or global rankings with peers.</p>
      </div>

      {/* Filter tab buttons */}
      <div className="flex border-b border-border text-xs font-semibold">
        <button 
          onClick={() => setActiveTab("global")}
          className={`pb-3 px-6 flex items-center gap-1.5 border-b-2 transition-all cursor-pointer ${
            activeTab === "global" ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-foreground"
          }`}
        >
          <Globe className="w-4 h-4" />
          Global Standings
        </button>
        <button 
          onClick={() => setActiveTab("monthly")}
          className={`pb-3 px-6 flex items-center gap-1.5 border-b-2 transition-all cursor-pointer ${
            activeTab === "monthly" ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-foreground"
          }`}
        >
          <Calendar className="w-4 h-4" />
          Monthly Standings
        </button>
        <button 
          onClick={() => setActiveTab("weekly")}
          className={`pb-3 px-6 flex items-center gap-1.5 border-b-2 transition-all cursor-pointer ${
            activeTab === "weekly" ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-foreground"
          }`}
        >
          <Zap className="w-4 h-4" />
          Weekly Standings
        </button>
      </div>

      {/* Podium Top 3 */}
      {!loading && rankings.length >= 3 && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-4 text-center"
        >
          {rankings.slice(0, 3).map((u) => (
            <div 
              key={u.user_id || u.rank} 
              className={`glass-panel rounded-2xl p-6 relative overflow-hidden flex flex-col items-center justify-between min-h-[200px] ${
                u.rank === 1 
                  ? "border-yellow-500/20 bg-yellow-500/5 order-1 sm:order-2 sm:-translate-y-4 shadow-lg shadow-yellow-500/5" 
                  : u.rank === 2 
                    ? "border-slate-400/20 bg-slate-400/5 order-2 sm:order-1" 
                    : "border-amber-600/20 bg-amber-600/5 order-3"
              }`}
            >
              <div className="space-y-2">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center font-black text-xs mx-auto ${
                  u.rank === 1 ? "bg-yellow-500 text-slate-950 shadow-lg shadow-yellow-500/20" : u.rank === 2 ? "bg-slate-400 text-slate-950" : "bg-amber-600 text-slate-950"
                }`}>
                  {u.rank}
                </span>
                <h3 className="font-extrabold text-foreground text-sm mt-2">{u.name}</h3>
                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block">{u.level}</span>
              </div>
              
              <div className="mt-4 text-xs">
                <span className="text-slate-550 block">Score</span>
                <span className="text-xl font-black text-primary block mt-0.5 glow-text">{u.points} XP</span>
              </div>
            </div>
          ))}
        </motion.div>
      )}

      {/* Detailed rankings list table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-border mt-8">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500">Retrieving standings...</div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border bg-slate-950/20 text-slate-400 font-bold">
                  <th className="p-4 w-16 text-center">Rank</th>
                  <th className="p-4">Name</th>
                  <th className="p-4">Standing Level</th>
                  <th className="p-4 text-right">Points / Period</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {rankings.map((u, idx) => (
                  <tr 
                    key={u.user_id || idx} 
                    className={`hover:bg-slate-950/10 text-foreground transition-colors ${
                      u.isMe ? "bg-emerald-600/10 dark:bg-emerald-950/20 text-primary" : ""
                    }`}
                  >
                    <td className="p-4 text-center font-black">{u.rank}</td>
                    <td className="p-4 font-bold flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center text-[10px] uppercase font-bold">
                        {u.name.substring(0, 2)}
                      </span>
                      {u.name} {u.isMe && <span className="text-[9px] uppercase tracking-wider bg-emerald-500/10 text-primary border border-emerald-500/20 px-1.5 py-0.5 rounded font-bold ml-2">YOU</span>}
                    </td>
                    <td className="p-4 text-slate-550 font-semibold">{u.level}</td>
                    <td className="p-4 text-right font-black text-primary">{u.points} XP</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  );
}
