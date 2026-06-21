"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Compass, Sparkles, RefreshCw, AlertTriangle, ShieldCheck, HelpCircle, DollarSign, Leaf, Plane, Zap } from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";
import { ChartDataPoint, SimulationResult } from "@/types";

export default function CarbonTwin() {
  const [buyEV, setBuyEV] = useState(false);
  const [installSolar, setInstallSolar] = useState(false);
  const [stopFlying, setStopFlying] = useState(false);
  const [reduceAC, setReduceAC] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const backendUrl = getBackendUrl("/twin/simulate");

  // Trigger simulation API call
  const runSimulation = async () => {
    setLoading(true);
    setError(null);

    const payload = {
      buy_ev: buyEV,
      install_solar: installSolar,
      stop_flying: stopFlying,
      reduce_ac: reduceAC
    };

    try {
      const res = await apiFetch(backendUrl, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        throw new Error("Failed to compute carbon twin adjustments");
      }
    } catch (err: any) {
      console.warn("FastAPI backend is offline. Using local simulation fallback.");
      // Fallback local calculations if backend fails
      setTimeout(() => {
        const original = 512.4;
        let projected = original;
        const sources: string[] = [];
        const savings: string[] = [];

        if (buyEV) {
          projected -= 142.3;
          sources.push("EV Commute (reduced tailpipe emissions)");
          savings.push("$90/month on gasoline");
        }
        if (installSolar) {
          projected -= 92.1;
          sources.push("Rooftop Solar generation");
          savings.push("$50/month on utility bill");
        }
        if (stopFlying) {
          projected -= 118.0;
          sources.push("Zero Aviation Flights");
          savings.push("$110/month on tickets (amortized)");
        }
        if (reduceAC) {
          projected -= 32.5;
          sources.push("Smart Thermostat (AC scheduling)");
          savings.push("$20/month on cooling");
        }

        const reduction = original - projected;
        const pct = original > 0 ? (reduction / original) * 100 : 0;
        
        // Generate chart data
        const months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"];
        const chartData = months.map((m, i) => {
          let multiplier = 1.0;
          if (i === 1 || i === 2) multiplier = 1.18; // Summer peak
          return {
            month: m,
            current: Math.round(original * multiplier),
            simulated: Math.round(projected * (buyEV || reduceAC ? 1.02 : multiplier))
          };
        });

        setResult({
          id: "fallback_id",
          original_co2_kg: Math.round(original),
          projected_co2_kg: Math.round(projected),
          reduction_kg: Math.round(reduction),
          reduction_pct: Math.round(pct),
          savings_usd_desc: savings.length > 0 ? `Total estimated savings: ${savings.join(" + ")}` : "No active savings",
          lifestyle_impact: "Making these adjustments moves your profile towards self-sufficiency and low grid draw. Compounding travel and heating improvements are highly effective.",
          top_savings_sources: sources.length > 0 ? sources : ["No active adjustments"],
          chart_data: chartData
        });
      }, 800);
    } finally {
      setLoading(false);
    }
  };

  // Re-run simulation whenever a toggle changes
  useEffect(() => {
    runSimulation();
  }, [buyEV, installSolar, stopFlying, reduceAC]);

  // Calculate ecology score based on reduction percentage
  const getEcologyScore = () => {
    if (!result) return 40;
    // Base score is 40. Max reduction pct pushes score up to 100.
    const score = 40 + Math.round(result.reduction_pct * 0.8);
    return Math.min(score, 100);
  };

  const score = getEcologyScore();

  // Find max value in chart data for visual scaling
  const getChartMax = () => {
    if (!result || !result.chart_data.length) return 100;
    const maxVal = Math.max(...result.chart_data.map(d => Math.max(d.current, d.simulated)));
    return maxVal * 1.15; // padding
  };

  const maxChartVal = getChartMax();

  return (
    <div className="space-y-10">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Virtual Carbon Twin</h1>
        <p className="text-muted text-xs mt-1.5">An interactive digital simulation modeling the impact of your lifestyle changes in real-time.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Visual Twin Simulation Card */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 flex flex-col justify-between min-h-[440px] bg-gradient-to-tr from-slate-950/20 to-transparent relative overflow-hidden">
          
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-550 uppercase tracking-widest font-bold">Simulation Render</span>
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest block font-bold">Ecology Score</span>
              <span className={`text-2xl font-black ${score > 70 ? "text-emerald-400" : score > 50 ? "text-blue-400" : "text-rose-455"}`}>
                {score}<span className="text-slate-650 text-xs">/100</span>
              </span>
            </div>
          </div>

          {/* SVG Animated Environment */}
          <div className="w-full h-64 relative flex items-center justify-center pt-6">
            <svg viewBox="0 0 400 200" className="w-full h-full max-w-md">
              <defs>
                {/* Sky gradients */}
                <linearGradient id="sky-smog" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1e293b" />
                  <stop offset="100%" stopColor="#453126" />
                </linearGradient>
                <linearGradient id="sky-clean" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0284c7" stopOpacity="0.45" />
                  <stop offset="100%" stopColor="#059669" stopOpacity="0.15" />
                </linearGradient>
              </defs>

              {/* Sky Background */}
              <rect x="0" y="0" width="400" height="200" fill={score > 60 ? "url(#sky-clean)" : "url(#sky-smog)"} rx="15" className="transition-all duration-700" />

              {/* Clouds / Smog Particles */}
              {score < 70 && (
                <g opacity="0.15">
                  <path d="M 50 40 Q 65 30 80 40 T 110 40 L 110 50 L 50 50 Z" fill="#94a3b8" />
                  <path d="M 280 60 Q 295 50 310 60 T 340 60 L 340 70 L 280 70 Z" fill="#94a3b8" />
                </g>
              )}

              {/* Flying Plane (Hidden if stopped flying) */}
              {!stopFlying && (
                <motion.g
                  animate={{ x: [-50, 450], y: [40, 20] }}
                  transition={{ repeat: Infinity, duration: 16, ease: "linear" }}
                >
                  {/* Plane body */}
                  <path d="M 10 10 L 25 10 L 30 7 L 33 7 L 32 10 L 38 10 L 39 12 L 10 12 Z" fill="#cbd5e1" />
                  {/* Plane wings */}
                  <polygon points="20,10 15,2 18,2 24,10" fill="#94a3b8" />
                  <polygon points="20,12 15,18 18,18 24,12" fill="#64748b" />
                  {/* Smoke Trail */}
                  {score < 75 && (
                    <line x1="-15" y1="11" x2="8" y2="11" stroke="#475569" strokeWidth="1.5" strokeDasharray="3,3" opacity="0.6" />
                  )}
                </motion.g>
              )}

              {/* Mountains/Hills */}
              <path d="M 0 160 Q 80 120 160 160 T 320 160 Q 360 140 400 170 L 400 200 L 0 200 Z" fill={score > 60 ? "#064e3b" : "#451a03"} className="transition-all duration-700" />
              <path d="M 0 180 Q 120 160 240 180 T 400 180 L 400 200 L 0 200 Z" fill={score > 70 ? "#047857" : "#543003"} className="transition-all duration-700" />

              {/* Smokestack Factory / Clean Windmill */}
              {!installSolar && !reduceAC ? (
                // Smog Factory
                <g transform="translate(80, 105)" className="transition-all duration-500">
                  <rect x="0" y="30" width="45" height="40" fill="#334155" />
                  <polygon points="10,30 15,10 23,10 18,30" fill="#475569" />
                  <polygon points="25,30 30,5 38,5 33,30" fill="#475569" />
                  {/* Thick Factory Smog animation */}
                  <motion.circle 
                    cx="33" cy="0" r="7" fill="#475569" opacity="0.7"
                    animate={{ y: [-5, -35], x: [33, 48], scale: [1, 1.8], opacity: [0.7, 0] }}
                    transition={{ repeat: Infinity, duration: 2.8, ease: "easeOut" }}
                  />
                  <motion.circle 
                    cx="18" cy="5" r="5" fill="#475569" opacity="0.6"
                    animate={{ y: [0, -25], x: [18, 28], scale: [1, 1.6], opacity: [0.6, 0] }}
                    transition={{ repeat: Infinity, duration: 2.2, ease: "easeOut", delay: 0.5 }}
                  />
                </g>
              ) : (
                // Clean wind turbine
                <g transform="translate(100, 80)">
                  <line x1="0" y1="80" x2="0" y2="0" stroke="#f1f5f9" strokeWidth="2.5" />
                  {/* Rotating Blades */}
                  <motion.g 
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 3.5, ease: "linear" }}
                  >
                    <line x1="0" y1="0" x2="0" y2="-28" stroke="#f1f5f9" strokeWidth="2" />
                    <line x1="0" y1="0" x2="24" y2="14" stroke="#f1f5f9" strokeWidth="2" />
                    <line x1="0" y1="0" x2="-24" y2="14" stroke="#f1f5f9" strokeWidth="2" />
                  </motion.g>
                </g>
              )}

              {/* Solar Panels Installation */}
              {installSolar && (
                <g transform="translate(250, 140)">
                  <polygon points="0,20 12,10 32,10 20,20" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="1" />
                  <polygon points="22,20 34,10 54,10 42,20" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="1" />
                </g>
              )}

              {/* Trees */}
              {score > 60 ? (
                // Forested landscape
                <g transform="translate(320, 120)">
                  <rect x="15" y="30" width="4" height="20" fill="#78350f" />
                  <circle cx="17" cy="23" r="10" fill="#10b981" />
                  <rect x="35" y="35" width="4" height="15" fill="#78350f" />
                  <circle cx="37" cy="30" r="8" fill="#047857" />
                </g>
              ) : (
                // Deforested dead tree stump
                <g transform="translate(330, 155)">
                  <line x1="15" y1="15" x2="15" y2="0" stroke="#78350f" strokeWidth="2.5" />
                  <line x1="11" y1="0" x2="19" y2="0" stroke="#78350f" strokeWidth="2" />
                </g>
              )}

              {/* EV Car */}
              {buyEV && (
                <motion.g 
                  initial={{ x: -60 }}
                  animate={{ x: [140, 190, 170] }}
                  transition={{ duration: 1.8, type: "spring" }}
                  transform="translate(0, 155)"
                >
                  <rect x="0" y="10" width="32" height="11" rx="3.5" fill="#10b981" />
                  <rect x="8" y="4" width="16" height="7" rx="2" fill="#a7f3d0" />
                  <circle cx="8" cy="21" r="3.5" fill="#0f172a" />
                  <circle cx="24" cy="21" r="3.5" fill="#0f172a" />
                  {/* Plug / green trail */}
                  <path d="M -3 14 L -6 14 L -6 11" stroke="#34d399" strokeWidth="1" fill="none" />
                </motion.g>
              )}
            </svg>
          </div>

          <div className="flex items-center gap-2 mt-4 px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-900 text-xs text-slate-400">
            {loading ? (
              <RefreshCw className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            )}
            <span>
              {loading 
                ? "Simulating changes on the ML model..." 
                : score > 75 
                  ? "Twin State: Clear. Emissions offset logs are high, creating a carbon-neutral digital environment." 
                  : "Twin State: Polluted. Activate green selectors on the sidebar to swap habits."}
            </span>
          </div>

        </div>

        {/* Adjustments Sidebar */}
        <div className="lg:col-span-1 glass-panel rounded-2xl p-6 space-y-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <Compass className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-foreground text-base">Twin Adjustments</h3>
            </div>

            <div className="space-y-4 text-xs">
              {/* Buy EV */}
              <button
                onClick={() => setBuyEV(!buyEV)}
                className={`w-full p-4 border rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                  buyEV ? "bg-emerald-950/20 text-emerald-400 border-emerald-500/20" : "bg-slate-950/40 border-slate-900 text-slate-500 hover:border-slate-800"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Leaf className="w-4.5 h-4.5" />
                  <span>Buy an EV</span>
                </div>
                <span className="font-mono font-bold">{buyEV ? "✓ Active" : "Simulate"}</span>
              </button>

              {/* Install Solar */}
              <button
                onClick={() => setInstallSolar(!installSolar)}
                className={`w-full p-4 border rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                  installSolar ? "bg-emerald-950/20 text-emerald-400 border-emerald-500/20" : "bg-slate-950/40 border-slate-900 text-slate-500 hover:border-slate-800"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Zap className="w-4.5 h-4.5" />
                  <span>Install solar panels</span>
                </div>
                <span className="font-mono font-bold">{installSolar ? "✓ Active" : "Simulate"}</span>
              </button>

              {/* Stop Flying */}
              <button
                onClick={() => setStopFlying(!stopFlying)}
                className={`w-full p-4 border rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                  stopFlying ? "bg-emerald-950/20 text-emerald-400 border-emerald-500/20" : "bg-slate-950/40 border-slate-900 text-slate-500 hover:border-slate-800"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Plane className="w-4.5 h-4.5" />
                  <span>Stop airplane travel</span>
                </div>
                <span className="font-mono font-bold">{stopFlying ? "✓ Active" : "Simulate"}</span>
              </button>

              {/* Reduce AC */}
              <button
                onClick={() => setReduceAC(!reduceAC)}
                className={`w-full p-4 border rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                  reduceAC ? "bg-emerald-950/20 text-emerald-400 border-emerald-500/20" : "bg-slate-950/40 border-slate-900 text-slate-500 hover:border-slate-800"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Sparkles className="w-4.5 h-4.5" />
                  <span>Reduce AC usage</span>
                </div>
                <span className="font-mono font-bold">{reduceAC ? "✓ Active" : "Simulate"}</span>
              </button>
            </div>
          </div>

          <div className="mt-8 text-[10px] text-slate-600 bg-slate-950/50 border border-slate-900/50 p-3.5 rounded-xl">
            <span className="font-semibold text-slate-500 block mb-1">How it works:</span>
            Toggling options updates variables inside the RandomForest/XGBoost ML pipeline to estimate the carbon reductions. Qualitative assessments are generated by Google Gemini.
          </div>
        </div>

      </div>

      {/* Projections & Report Section */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-8"
          >
            {/* Metric summaries */}
            <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6">
              
              <div className="glass-panel rounded-xl p-5 space-y-1.5 bg-slate-950/40">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block">Current Footprint</span>
                <span className="text-3xl font-black text-slate-450 block">{result.original_co2_kg} <span className="text-sm font-normal text-slate-550">kg CO2/mo</span></span>
              </div>

              <div className="glass-panel rounded-xl p-5 space-y-1.5 border-emerald-500/20 bg-gradient-to-tr from-emerald-950/15 to-transparent">
                <span className="text-[10px] text-emerald-450 uppercase tracking-widest font-bold block">Simulated Footprint</span>
                <span className="text-3xl font-black text-emerald-400 block">{result.projected_co2_kg} <span className="text-sm font-normal text-emerald-600">kg CO2/mo</span></span>
              </div>

              <div className="glass-panel rounded-xl p-5 space-y-1.5 border-blue-500/20 bg-gradient-to-tr from-blue-950/15 to-transparent">
                <span className="text-[10px] text-blue-450 uppercase tracking-widest font-bold block">Simulated Reduction</span>
                <span className="text-3xl font-black text-blue-400 block">
                  -{result.reduction_kg} <span className="text-sm font-normal text-blue-550">kg</span>
                  <span className="text-xs font-bold text-emerald-400 ml-2">({result.reduction_pct}%)</span>
                </span>
              </div>

            </div>

            {/* Custom SVG Grouped Bar Chart */}
            <div className="lg:col-span-2 glass-panel rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-foreground text-sm">6-Month Carbon Footprint Projection</h3>
                <div className="flex items-center gap-4 text-[10px] font-bold">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 bg-rose-500 rounded-sm" />
                    <span className="text-slate-450">Current Baseline</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 bg-emerald-400 rounded-sm" />
                    <span className="text-slate-450">Simulated Footprint</span>
                  </div>
                </div>
              </div>

              {/* Render Custom SVG Chart */}
              <div className="w-full pt-4 flex justify-center">
                <svg viewBox="0 0 500 220" className="w-full max-w-lg h-52">
                  {/* Grid Lines */}
                  <line x1="40" y1="30" x2="480" y2="30" stroke="#1e293b" strokeWidth="1" strokeDasharray="4,4" />
                  <line x1="40" y1="100" x2="480" y2="100" stroke="#1e293b" strokeWidth="1" strokeDasharray="4,4" />
                  <line x1="40" y1="170" x2="480" y2="170" stroke="#334155" strokeWidth="1" />

                  {/* Y Axis Labels */}
                  <text x="32" y="34" fill="#64748b" fontSize="8" textAnchor="end" fontFamily="monospace">
                    {Math.round(maxChartVal)}
                  </text>
                  <text x="32" y="104" fill="#64748b" fontSize="8" textAnchor="end" fontFamily="monospace">
                    {Math.round(maxChartVal / 2)}
                  </text>
                  <text x="32" y="174" fill="#64748b" fontSize="8" textAnchor="end" fontFamily="monospace">
                    0
                  </text>

                  {/* Render Data Bars */}
                  {result.chart_data.map((d, idx) => {
                    const xCenter = 50 + idx * 72;
                    
                    const hCurrent = (d.current / maxChartVal) * 140;
                    const hSimulated = (d.simulated / maxChartVal) * 140;
                    
                    const yCurrent = 170 - hCurrent;
                    const ySimulated = 170 - hSimulated;

                    return (
                      <g key={idx}>
                        {/* Current Bar */}
                        <motion.rect
                          x={xCenter + 8}
                          y={170}
                          width="16"
                          rx="3"
                          fill="#f43f5e"
                          opacity="0.85"
                          animate={{ y: yCurrent, height: hCurrent }}
                          transition={{ duration: 0.8, ease: "easeOut" }}
                        />
                        {/* Simulated Bar */}
                        <motion.rect
                          x={xCenter + 28}
                          y={170}
                          width="16"
                          rx="3"
                          fill="#10b981"
                          opacity="0.9"
                          animate={{ y: ySimulated, height: hSimulated }}
                          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
                        />

                        {/* Hover values (rendered smaller on top) */}
                        <text x={xCenter + 16} y={yCurrent - 4} fill="#fda4af" fontSize="7" textAnchor="middle" fontWeight="bold">
                          {Math.round(d.current)}
                        </text>
                        <text x={xCenter + 36} y={ySimulated - 4} fill="#a7f3d0" fontSize="7" textAnchor="middle" fontWeight="bold">
                          {Math.round(d.simulated)}
                        </text>

                        {/* Month Label */}
                        <text x={xCenter + 26} y="190" fill="#94a3b8" fontSize="9" textAnchor="middle" fontWeight="bold">
                          {d.month}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* Gemini Report Card */}
            <div className="lg:col-span-1 space-y-6">
              
              {/* Financial Savings Card */}
              <div className="glass-panel rounded-2xl p-6 bg-slate-950/20 border border-slate-900">
                <div className="flex items-center gap-2.5 mb-3 text-amber-450">
                  <DollarSign className="w-5 h-5" />
                  <h4 className="font-bold text-foreground text-sm">Financial Forecast</h4>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-bold">
                  {result.savings_usd_desc}
                </p>
              </div>

              {/* Lifestyle impact Card */}
              <div className="glass-panel rounded-2xl p-6 space-y-4">
                <div className="space-y-1">
                  <h4 className="font-bold text-foreground text-sm">Lifestyle Twin Report</h4>
                  <span className="text-[10px] text-emerald-400 font-bold block uppercase tracking-wider">Generated by EcoPilot Coach</span>
                </div>
                
                <p className="text-xs text-slate-350 leading-relaxed">
                  {result.lifestyle_impact}
                </p>

                <div className="border-t border-slate-900 pt-4 space-y-3">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block">Top Offset Sources</span>
                  <div className="space-y-2">
                    {result.top_savings_sources.map((src, i) => (
                      <div key={i} className="flex items-center gap-2 text-[11px] text-slate-300">
                        <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                        <span>{src}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </div>

          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
