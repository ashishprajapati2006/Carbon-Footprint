"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Leaf, Car, Zap, Trash2, Calendar, TrendingUp, CheckCircle, ArrowRight, Compass
} from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";

// Mock Fallbacks
const DEFAULT_LOGS = [
  { _id: "1", date: "2026-06-15", categories: { energy: { co2_kg: 140 }, transport: { co2_kg: 120 }, food: { co2_kg: 150 }, waste: { co2_kg: 30 } }, total_co2_kg: 440 },
  { _id: "2", date: "2026-05-15", categories: { energy: { co2_kg: 160 }, transport: { co2_kg: 140 }, food: { co2_kg: 150 }, waste: { co2_kg: 35 } }, total_co2_kg: 485 },
  { _id: "3", date: "2026-04-15", categories: { energy: { co2_kg: 180 }, transport: { co2_kg: 210 }, food: { co2_kg: 150 }, waste: { co2_kg: 40 } }, total_co2_kg: 580 },
];

const DEFAULT_PREDICTIONS = [
  { date: "2026-07", co2_kg: 410, confidence: "medium" },
  { date: "2026-08", co2_kg: 390, confidence: "medium" },
  { date: "2026-09", co2_kg: 360, confidence: "medium" },
];

export default function Dashboard() {
  const [logs, setLogs] = useState<any[]>(DEFAULT_LOGS);
  const [predictions, setPredictions] = useState<any[]>(DEFAULT_PREDICTIONS);
  const [loading, setLoading] = useState(true);
  
  // Form State
  const [kwh, setKwh] = useState("");
  const [distance, setDistance] = useState("");
  const [vehicle, setVehicle] = useState("petrol");
  const [diet, setDiet] = useState("omnivore");
  const [waste, setWaste] = useState("");
  const [recycled, setRecycled] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const backendUrl = getBackendUrl();

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const logsRes = await apiFetch(`${backendUrl}/footprint/history`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        if (logsData.length > 0) setLogs(logsData);
      }
      
      const predRes = await apiFetch(`${backendUrl}/footprint/predict`);
      if (predRes.ok) {
        const predData = await predRes.json();
        if (predData.length > 0) setPredictions(predData);
      }
    } catch (err) {
      console.warn("Could not connect to FastAPI backend. Rendering fallback dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleLogSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSuccessMsg("");

    const payload = {
      energy: kwh ? { kwh: parseFloat(kwh), co2_kg: 0 } : undefined,
      transport: distance ? { distance_km: parseFloat(distance), mode: vehicle, co2_kg: 0 } : undefined,
      food: { diet_type: diet, co2_kg: 0 },
      waste: waste ? { waste_weight_kg: parseFloat(waste), recycled: recycled, co2_kg: 0 } : undefined,
      date: new Date().toISOString()
    };

    try {
      const response = await apiFetch(`${backendUrl}/footprint/log`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const newLog = await response.json();
        setLogs(prev => [newLog, ...prev]);
        setSuccessMsg("Habits logged successfully!");
        setKwh("");
        setDistance("");
        setWaste("");
        
        // Refresh predictions
        const predRes = await apiFetch(`${backendUrl}/footprint/predict`);
        if (predRes.ok) {
          const predData = await predRes.json();
          setPredictions(predData);
        }
      } else {
        throw new Error("API responded with an error");
      }
    } catch (err) {
      // Offline fallback simulate log entry
      console.warn("Backend offline. Simulating logger values locally.");
      
      const eCo2 = (parseFloat(kwh) || 0) * 0.4;
      const tFactors: any = { ev: 0.05, petrol: 0.18, diesel: 0.20, public: 0.04, flight: 0.25, bicycle: 0.0, none: 0.0 };
      const tCo2 = (parseFloat(distance) || 0) * (tFactors[vehicle] || 0.0);
      const fFactors: any = { vegan: 2.0, vegetarian: 3.5, omnivore: 5.0, high_meat: 8.0 };
      const fCo2 = (fFactors[diet] || 5.0) * 30; // Monthly estimate
      const wCo2 = (parseFloat(waste) || 0) * (recycled ? 0.1 : 0.5);
      
      const total = eCo2 + tCo2 + fCo2 + wCo2;
      const newMockLog = {
        _id: String(Date.now()),
        date: new Date().toISOString().split("T")[0],
        categories: {
          energy: { co2_kg: Math.round(eCo2) },
          transport: { co2_kg: Math.round(tCo2) },
          food: { co2_kg: Math.round(fCo2) },
          waste: { co2_kg: Math.round(wCo2) }
        },
        total_co2_kg: Math.round(total)
      };

      setLogs(prev => [newMockLog, ...prev]);
      setSuccessMsg("Habits logged locally (Demo Mode)!");
      setKwh("");
      setDistance("");
      setWaste("");
    } finally {
      setSubmitting(false);
      setTimeout(() => setSuccessMsg(""), 3000);
    }
  };

  const getRating = (co2: number) => {
    if (co2 < 300) return { title: "Eco-Warrior", color: "text-emerald-400 dark:text-emerald-400", bg: "bg-emerald-950/20", pct: 15 };
    if (co2 < 500) return { title: "Green Citizen", color: "text-blue-400 dark:text-blue-450", bg: "bg-blue-950/20", pct: 50 };
    return { title: "Carbon Heavy", color: "text-amber-500 dark:text-amber-500", bg: "bg-amber-950/20", pct: 85 };
  };

  const currentMonthLog = logs[0] || { total_co2_kg: 450 };
  const rating = getRating(currentMonthLog.total_co2_kg);

  // Chart plotting helper
  const allChartData = [
    ...logs.slice(0, 3).map(l => ({ label: l.date.substring(5, 7) + "/" + l.date.substring(2, 4), val: l.total_co2_kg, type: "actual" })).reverse(),
    ...predictions.map(p => ({ label: p.date, val: p.co2_kg, type: "predicted" }))
  ];

  return (
    <div className="space-y-10">
      {/* Welcome Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Eco Dashboard</h1>
          <p className="text-muted text-xs mt-1.5">Track, audit, and simulate your ecological footprint in real-time.</p>
        </div>
        <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl glass-panel text-muted text-xs font-semibold self-start">
          <Calendar className="w-4 h-4 text-primary" />
          <span>Status: Green Sandbox Active</span>
        </div>
      </div>

      {/* Hero Stats Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Carbon Progress Ring Card */}
        <div className="lg:col-span-1 glass-panel rounded-2xl p-6 flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
          
          <h3 className="text-xs font-semibold text-muted uppercase tracking-widest text-center self-start mb-6">Current Month Impact</h3>
          
          <div className="relative w-40 h-40 flex items-center justify-center">
            {/* SVG circle track */}
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="80" cy="80" r="68" stroke="rgba(16,185,129,0.06)" strokeWidth="10" fill="transparent" />
              <motion.circle 
                cx="80" 
                cy="80" 
                r="68" 
                stroke="#10b981" 
                strokeWidth="10" 
                fill="transparent" 
                strokeDasharray="427"
                initial={{ strokeDashoffset: 427 }}
                animate={{ strokeDashoffset: 427 - (427 * Math.min(currentMonthLog.total_co2_kg, 800)) / 800 }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute text-center">
              <span className="text-3xl font-black text-foreground glow-text block">{currentMonthLog.total_co2_kg}</span>
              <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold block mt-0.5">KG CO2e</span>
            </div>
          </div>

          <div className="w-full mt-6 text-center">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${rating.bg} ${rating.color}`}>
              <Leaf className="w-3.5 h-3.5" />
              {rating.title}
            </span>
            <p className="text-[10px] text-slate-500 mt-2">Emission levels are calculated in real-time according to logged factors.</p>
          </div>
        </div>

        {/* Predictive Trend Graph */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-3xl" />
          
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xs font-semibold text-muted uppercase tracking-widest">Emissions Projections</h3>
              <p className="text-[10px] text-slate-500">FastAPI least-squares regression predictions.</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-primary"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />Actual</span>
              <span className="flex items-center gap-1.5 text-secondary"><span className="w-2.5 h-2.5 rounded-full bg-blue-500" />Forecasted</span>
            </div>
          </div>

          {/* SVG Line Graph */}
          <div className="h-44 w-full relative">
            {allChartData.length > 0 ? (
              <svg className="w-full h-full" viewBox="0 0 500 150" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="actual-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.25"/>
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0"/>
                  </linearGradient>
                  <linearGradient id="pred-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25"/>
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0"/>
                  </linearGradient>
                </defs>
                
                {/* Grid Lines */}
                <line x1="0" y1="37.5" x2="500" y2="37.5" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                <line x1="0" y1="75" x2="500" y2="75" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                <line x1="0" y1="112.5" x2="500" y2="112.5" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />

                {/* SVG path creation */}
                {(() => {
                  const width = 500;
                  const height = 150;
                  const maxVal = Math.max(...allChartData.map(d => d.val), 600);
                  const points = allChartData.map((d, index) => {
                    const x = (width / (allChartData.length - 1)) * index;
                    const y = height - (d.val / maxVal) * (height - 30) - 15;
                    return { x, y, label: d.label, val: d.val, type: d.type };
                  });

                  const actualPoints = points.filter(p => p.type === "actual");
                  const predPoints = points.filter(p => p.type === "predicted");

                  const actualPath = actualPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
                  const predPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

                  return (
                    <>
                      {/* Paths */}
                      <path d={predPath} fill="none" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4,4" />
                      <path d={actualPath} fill="none" stroke="#10b981" strokeWidth="3.5" />
                      
                      {/* Fills */}
                      {actualPoints.length > 1 && (
                        <path 
                          d={`${actualPath} L ${actualPoints[actualPoints.length - 1].x} 150 L ${actualPoints[0].x} 150 Z`} 
                          fill="url(#actual-grad)" 
                        />
                      )}

                      {/* Circles for values */}
                      {points.map((p, i) => (
                        <g key={i}>
                          <circle cx={p.x} cy={p.y} r="4" fill={p.type === "actual" ? "#10b981" : "#3b82f6"} />
                          <text x={p.x} y={p.y - 10} fill="#94a3b8" fontSize="8" textAnchor="middle" fontWeight="bold">
                            {p.val}
                          </text>
                          <text x={p.x} y="145" fill="#64748b" fontSize="8" textAnchor="middle">
                            {p.label}
                          </text>
                        </g>
                      ))}
                    </>
                  );
                })()}
              </svg>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-xs">No chart statistics available.</div>
            )}
          </div>
          
          <div className="flex items-center gap-2 mt-4 px-3 py-1.5 rounded-lg bg-emerald-950/10 border border-emerald-950/20 text-primary text-xs">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>AI Emission Trend: Downward trajectory projected due to simulated behavioral enhancements.</span>
          </div>
        </div>

      </div>

      {/* Logging & Navigation Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Habit Logger Form */}
        <div className="lg:col-span-1 glass-panel rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <Leaf className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-foreground text-lg">Log Today's Habits</h3>
          </div>

          <form onSubmit={handleLogSubmit} className="space-y-4 text-xs">
            {/* Energy */}
            <div className="space-y-1">
              <label htmlFor="kwh-input" className="text-muted font-semibold flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                Electricity Usage (kWh)
              </label>
              <input 
                id="kwh-input"
                type="number" 
                placeholder="e.g. 15"
                value={kwh}
                onChange={e => setKwh(e.target.value)}
                className="w-full bg-slate-950/50 dark:bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>

            {/* Transport */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="distance-input" className="text-muted font-semibold flex items-center gap-1.5">
                  <Car className="w-3.5 h-3.5 text-blue-500" />
                  Distance (km)
                </label>
                <input 
                  id="distance-input"
                  type="number" 
                  placeholder="e.g. 35"
                  value={distance}
                  onChange={e => setDistance(e.target.value)}
                  className="w-full bg-slate-950/50 dark:bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="vehicle-select" className="text-muted font-semibold">Vehicle Type</label>
                <select 
                  id="vehicle-select"
                  value={vehicle}
                  onChange={e => setVehicle(e.target.value)}
                  className="w-full bg-slate-950/50 dark:bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
                >
                  <option value="petrol">Petrol Car</option>
                  <option value="diesel">Diesel Car</option>
                  <option value="ev">Electric (EV)</option>
                  <option value="public">Transit / Bus</option>
                  <option value="flight">Flight</option>
                  <option value="bicycle">Bicycle / Walk</option>
                </select>
              </div>
            </div>

            {/* Diet */}
            <div className="space-y-1">
              <label htmlFor="diet-select" className="text-muted font-semibold">Diet Log</label>
              <select 
                id="diet-select"
                value={diet}
                onChange={e => setDiet(e.target.value)}
                className="w-full bg-slate-950/50 dark:bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
              >
                <option value="omnivore">Omnivore (Default)</option>
                <option value="high_meat">Heavy Meat Diet</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
              </select>
            </div>

            {/* Waste */}
            <div className="space-y-1">
              <label htmlFor="waste-input" className="text-muted font-semibold flex items-center gap-1.5">
                <Trash2 className="w-3.5 h-3.5 text-slate-550" />
                Waste Weight (kg)
              </label>
              <div className="flex gap-2">
                <input 
                  id="waste-input"
                  type="number" 
                  placeholder="e.g. 5"
                  value={waste}
                  onChange={e => setWaste(e.target.value)}
                  className="w-full bg-slate-950/50 dark:bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setRecycled(!recycled)}
                  aria-pressed={recycled}
                  className={`px-3 border rounded-lg transition-colors font-bold ${recycled ? "bg-emerald-950/30 text-primary border-emerald-500" : "bg-slate-955 border-border text-slate-500"}`}
                >
                  Recycled
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              disabled={submitting}
              className="w-full py-3 rounded-lg text-white font-bold glow-btn transition-all flex items-center justify-center gap-2 mt-4 cursor-pointer"
            >
              {submitting ? "Calculating..." : "Compute & Save Today's Footprint"}
            </button>

            <AnimatePresence>
              {successMsg && (
                <motion.div 
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-500/20 text-primary text-xs font-semibold"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>{successMsg}</span>
                </motion.div>
              )}
            </AnimatePresence>
          </form>
        </div>

        {/* Quick Navigate & Platform Actions */}
        <div className="lg:col-span-2 flex flex-col justify-between gap-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 h-full">
            
            {/* Bill Scan Card */}
            <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between glass-panel-hover">
              <div>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-500/10 mb-4">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-bold text-foreground text-base">Utility Bill Audit</h4>
                <p className="text-xs text-muted mt-1.5 leading-relaxed">Upload a utility statement to automatically extract kWh values and track electricity emissions.</p>
              </div>
              <a 
                href="/bills"
                className="mt-6 inline-flex items-center gap-1.5 text-xs text-amber-500 hover:text-amber-600 font-bold transition-all self-start"
              >
                Scan Utility Bill
                <ArrowRight className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Room Scan Card */}
            <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between glass-panel-hover">
              <div>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/10 mb-4">
                  <Compass className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-bold text-foreground text-base">Room Eco Scanner</h4>
                <p className="text-xs text-muted mt-1.5 leading-relaxed">Capture a room photo to identify high electrical loads and receive recommended energy swaps.</p>
              </div>
              <a 
                href="/rooms"
                className="mt-6 inline-flex items-center gap-1.5 text-xs text-secondary hover:text-blue-600 font-bold transition-all self-start"
              >
                Scan Appliances
                <ArrowRight className="w-3.5 h-3.5" />
              </a>
            </div>

          </div>

          {/* Simulator Banner */}
          <div className="w-full glass-panel rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-6 relative overflow-hidden bg-gradient-to-r from-emerald-950/10 to-blue-950/10">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
            <div className="space-y-1.5">
              <h4 className="font-bold text-foreground text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary" />
                Sandbox Lifestyle Simulator
              </h4>
              <p className="text-xs text-muted max-w-xl">
                Simulate swapping vehicle types, installing rooftop solar panels, or transitioning your diet to see potential carbon footprint offsets.
              </p>
            </div>
            <a 
              href="/simulator"
              className="py-3 px-6 rounded-full text-foreground bg-slate-900/10 hover:bg-slate-800/10 text-xs font-bold border border-border shadow-xl transition-all whitespace-nowrap cursor-pointer"
            >
              Open Simulator
            </a>
          </div>

        </div>

      </div>
    </div>
  );
}
