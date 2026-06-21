"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Compass, Sparkles, CheckSquare, RefreshCw, Leaf, ArrowRight, Zap, Car } from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";

export default function Simulator() {
  const [vehicle, setVehicle] = useState("petrol");
  const [diet, setDiet] = useState("omnivore");
  const [solar, setSolar] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const backendUrl = getBackendUrl("/footprint/simulate");

  const triggerSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    setResult(null);

    const payload = {
      change_transport_mode: vehicle !== "petrol" ? vehicle : undefined,
      diet_change: diet !== "omnivore" ? diet : undefined,
      solar_installation: solar ? true : undefined
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
        throw new Error("Sim failed");
      }
    } catch (err) {
      // Backend offline fallback simulation
      setTimeout(() => {
        let original = 455.0;
        let projected = original;
        const recs = [];

        if (vehicle !== "petrol") {
          projected -= 80.0;
          recs.push(`Switching travel commute to ${vehicle} offsets emissions.`);
        }
        if (diet !== "omnivore") {
          projected -= 45.0;
          recs.push(`Transitioning to a ${diet} menu configuration offsets emissions.`);
        }
        if (solar) {
          projected -= 140.0;
          recs.push("Rooftop solar installation offsets grid consumption by 80%.");
        }

        const savings = Math.max(0, original - projected);
        const savingsPct = Math.round((savings / original) * 100);

        setResult({
          original_co2_kg: Math.round(original),
          projected_co2_kg: Math.round(projected),
          potential_saving_percentage: savingsPct,
          recommendations: recs.length > 0 ? recs : ["Try selecting a transport or dietary swap to simulate carbon offsets."]
        });
        setSimulating(false);
      }, 1000);
      return;
    }
    setSimulating(false);
  };

  return (
    <div className="space-y-10">
      {/* Title */}
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">Lifestyle Simulator</h1>
        <p className="text-slate-400 text-sm mt-1.5">Configure carbon habit adjustments to view offsets and green metrics projections.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Input Panel */}
        <div className="lg:col-span-1 glass-panel rounded-2xl p-6 h-fit">
          <div className="flex items-center gap-2 mb-6">
            <Compass className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-white text-base">Adjust Parameters</h3>
          </div>

          <form onSubmit={triggerSimulation} className="space-y-5 text-xs">
            {/* Travel commute */}
            <div className="space-y-1">
              <label htmlFor="vehicle-select" className="text-slate-450 font-semibold flex items-center gap-1.5">
                <Car className="w-3.5 h-3.5 text-blue-500" />
                Transit Commute Swap
              </label>
              <select 
                id="vehicle-select"
                value={vehicle}
                onChange={e => setVehicle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-3 text-slate-350 focus:outline-none focus:border-emerald-500"
              >
                <option value="petrol">Petrol Sedan (Baseline)</option>
                <option value="diesel">Diesel Car</option>
                <option value="ev">Electric Vehicle (EV)</option>
                <option value="public">Public Transit</option>
                <option value="bicycle">Bicycle / Walk</option>
              </select>
            </div>

            {/* Diet choice */}
            <div className="space-y-1">
              <label htmlFor="diet-select" className="text-slate-450 font-semibold flex items-center gap-1.5">
                <Leaf className="w-3.5 h-3.5 text-emerald-500" />
                Culinary Dietary Choice
              </label>
              <select 
                id="diet-select"
                value={diet}
                onChange={e => setDiet(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-3 text-slate-350 focus:outline-none focus:border-emerald-500"
              >
                <option value="omnivore">Omnivore (Baseline)</option>
                <option value="high_meat">Heavy Meat Consumed</option>
                <option value="vegetarian">Vegetarian Shift</option>
                <option value="vegan">Vegan Shift</option>
              </select>
            </div>

            {/* Energy option */}
            <div className="space-y-1">
              <label htmlFor="solar-button" className="text-slate-450 font-semibold flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                Residential Upgrades
              </label>
              <button 
                id="solar-button"
                type="button"
                onClick={() => setSolar(!solar)}
                aria-pressed={solar}
                className={`w-full py-2.5 px-3 border rounded-lg transition-all text-left font-bold ${
                  solar ? "bg-amber-950/20 text-amber-400 border-amber-500" : "bg-slate-950 border-slate-800 text-slate-500"
                }`}
              >
                {solar ? "✓ Solar Panels Selected" : "Install Rooftop Solar Panels"}
              </button>
            </div>

            <button 
              type="submit"
              disabled={simulating}
              className="w-full py-3 rounded-lg text-white font-bold glow-btn transition-all flex items-center justify-center gap-2 cursor-pointer mt-6"
            >
              <RefreshCw className={`w-4 h-4 ${simulating ? "animate-spin" : ""}`} />
              Run Footprint Simulator
            </button>
          </form>
        </div>

        {/* Projections Panel */}
        <div className="lg:col-span-2 space-y-6">
          <AnimatePresence mode="wait">
            {!result ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-panel rounded-2xl p-16 flex flex-col items-center justify-center text-center space-y-4 h-full min-h-[300px]"
              >
                <Sparkles className="w-10 h-10 text-emerald-400/50 animate-pulse" />
                <p className="text-sm font-bold text-slate-350">Simulation Results Sandbox</p>
                <p className="text-xs text-slate-500 max-w-sm">Adjust lifestyle inputs on the side panel and trigger simulation models to forecast emissions reductions.</p>
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {/* Result Summary Bar */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
                  
                  <div className="glass-panel rounded-xl p-5 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block">Current Average</span>
                    <span className="text-3xl font-black text-slate-400 block mt-1">{result.original_co2_kg} kg</span>
                  </div>

                  <div className="glass-panel rounded-xl p-5 space-y-1 relative border-emerald-500/20 bg-gradient-to-tr from-emerald-950/10 to-transparent">
                    <span className="text-[10px] text-emerald-450 uppercase tracking-widest font-bold block">Projected Average</span>
                    <span className="text-3xl font-black text-emerald-400 block mt-1">{result.projected_co2_kg} kg</span>
                  </div>

                  <div className="glass-panel rounded-xl p-5 space-y-1 border-blue-500/20 bg-gradient-to-tr from-blue-950/10 to-transparent">
                    <span className="text-[10px] text-blue-450 uppercase tracking-widest font-bold block">Carbon Reduction</span>
                    <span className="text-3xl font-black text-blue-400 block mt-1">{result.potential_saving_percentage}%</span>
                  </div>

                </div>

                {/* Recommendations */}
                <div className="glass-panel rounded-2xl p-6 space-y-4">
                  <h4 className="font-bold text-white text-sm">Targeted Reduction Checklist</h4>
                  <div className="space-y-3">
                    {result.recommendations.map((rec: string, i: number) => (
                      <div key={i} className="p-3.5 rounded-xl bg-slate-950 border border-slate-900 flex items-start gap-3 text-xs text-slate-300">
                        <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>

              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
}
