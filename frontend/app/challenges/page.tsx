"use client";

import React, { useState, useEffect } from "react";
import { getBackendUrl, apiFetch } from "@/services/api";
import { LevelIndicator } from "@/components/challenges/LevelIndicator";
import { QuestCard } from "@/components/challenges/QuestCard";

/** A sustainability challenge/quest record returned by the API. */
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

/**
 * Eco Challenges page — Gamified Carbon Reduction Quests.
 */
export default function Challenges() {
  const [userXp, setUserXp] = useState(380);
  const [quests, setQuests] = useState<EcoChallenge[]>([]);
  const [loading, setLoading] = useState(true);
  
  const initialQuests: EcoChallenge[] = [
    { id: "q1", quest_title: "Meatless Commute", description: "Eat vegetarian or vegan meals for 3 consecutive days.", xp_yield: 120, category: "food", goal_amount: 3, current_amount: 2, status: "in_progress" },
    { id: "q2", quest_title: "Transit Traveler", description: "Swap driving single commutes for rail or bus travel.", xp_yield: 150, category: "transport", goal_amount: 1, current_amount: 0, status: "in_progress" },
    { id: "q3", quest_title: "Standby Shutdown", description: "Audit and unplug 5 idle phantom electrical loads.", xp_yield: 60, category: "energy", goal_amount: 5, current_amount: 5, status: "completed" },
    { id: "q4", quest_title: "Refuse Restraint", description: "Keep household waste below 5kg this week.", xp_yield: 80, category: "waste", goal_amount: 1, current_amount: 1, status: "completed" }
  ];

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

  return (
    <div className="space-y-10">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Eco Challenges</h1>
          <p className="text-muted text-xs mt-1.5">Participate in sustainability tasks, log progress, and claim ecological XP rewards.</p>
        </div>

        {/* User Level Indicator */}
        <LevelIndicator userXp={userXp} />
      </div>

      {/* Challenges Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs">Retrieving active challenges...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {quests.map((q) => (
            <QuestCard key={q.id} quest={q} onClaim={handleClaim} />
          ))}
        </div>
      )}
    </div>
  );
}
