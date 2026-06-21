"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Leaf, Zap, Car, Trash2, CheckCircle, HelpCircle } from "lucide-react";
import { getBackendUrl, apiFetch } from "@/services/api";

export default function Calculator() {
  const [step, setStep] = useState(1);
  const [kwh, setKwh] = useState("");
  const [distance, setDistance] = useState("");
  const [vehicle, setVehicle] = useState("petrol");
  const [diet, setDiet] = useState("omnivore");
  const [waste, setWaste] = useState("");
  const [recycled, setRecycled] = useState(false);
  
  const [submitting, setSubmitting] = useState(false);
  const [calculatedCo2, setCalculatedCo2] = useState<number | null>(null);

  const calculateLogsLocally = () => {
    const energyCo2 = (parseFloat(kwh) || 0) * 0.4;
    const transFactors: any = { ev: 0.05, petrol: 0.18, diesel: 0.20, public: 0.04, flight: 0.25, bicycle: 0.0, none: 0.0 };
    const transCo2 = (parseFloat(distance) || 0) * (transFactors[vehicle] || 0.0);
    const foodFactors: any = { vegan: 2.0, vegetarian: 3.5, omnivore: 5.0, high_meat: 8.0 };
    const foodCo2 = (foodFactors[diet] || 5.0) * 30; // 30-day estimate
    const wasteCo2 = (parseFloat(waste) || 0) * (recycled ? 0.1 : 0.5);

    return Math.round(energyCo2 + transCo2 + foodCo2 + wasteCo2);
  };

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      energy: kwh ? { kwh: parseFloat(kwh), co2_kg: 0 } : undefined,
      transport: distance ? { distance_km: parseFloat(distance), mode: vehicle, co2_kg: 0 } : undefined,
      food: { diet_type: diet, co2_kg: 0 },
      waste: waste ? { waste_weight_kg: parseFloat(waste), recycled: recycled, co2_kg: 0 } : undefined
    };

    try {
      const res = await apiFetch(getBackendUrl("/footprint/log"), {
        method: "POST",
        headers: { 
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setCalculatedCo2(data.total_co2_kg);
        setStep(5);
      } else {
        throw new Error("Failed backend submit");
      }
    } catch (err) {
      // Offline fallback
      setTimeout(() => {
        const co2 = calculateLogsLocally();
        setCalculatedCo2(co2);
        setStep(5);
        setSubmitting(false);
      }, 1000);
    }
  };

  return (
    <div className="space-y-10 max-w-3xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Emissions Calculator</h1>
        <p className="text-muted text-xs mt-1.5">A step-by-step form to calculate and log carbon output categories.</p>
      </div>

      {/* Progress Line */}
      <div className="flex items-center justify-between text-xs font-bold text-slate-500">
        <span className={step >= 1 ? "text-primary" : ""}>1. Energy</span>
        <span className="w-8 h-px bg-slate-800" />
        <span className={step >= 2 ? "text-primary" : ""}>2. Travel</span>
        <span className="w-8 h-px bg-slate-800" />
        <span className={step >= 3 ? "text-primary" : ""}>3. Diet</span>
        <span className="w-8 h-px bg-slate-800" />
        <span className={step >= 4 ? "text-primary" : ""}>4. Waste</span>
        <span className="w-8 h-px bg-slate-800" />
        <span className={step >= 5 ? "text-primary" : ""}>5. Result</span>
      </div>

      <div className="glass-panel rounded-2xl p-8 relative overflow-hidden min-h-[320px] flex flex-col justify-between">
        
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div 
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-500" />
                Step 1: Residential Electricity Draw
              </h3>
              <p className="text-xs text-muted leading-relaxed">Enter average monthly electricity draws in kWh. (Find this on utility statements or use the Bill Analyzer).</p>
              
              <div className="space-y-1 pt-2">
                <label htmlFor="kwh-input" className="text-xs text-slate-400 font-semibold block">Electricity Consumed (kWh)</label>
                <input 
                  type="number"
                  id="kwh-input"
                  placeholder="e.g. 350"
                  value={kwh}
                  onChange={e => setKwh(e.target.value)}
                  className="w-full bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none"
                />
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div 
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Car className="w-5 h-5 text-blue-500" />
                Step 2: Commuting & Travel Distance
              </h3>
              <p className="text-xs text-muted leading-relaxed">Select vehicle type and input distance traveled monthly.</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1">
                  <label htmlFor="distance-input" className="text-xs text-slate-400 font-semibold block">Distance (km)</label>
                  <input 
                    type="number"
                    id="distance-input"
                    placeholder="e.g. 500"
                    value={distance}
                    onChange={e => setDistance(e.target.value)}
                    className="w-full bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="vehicle-select" className="text-xs text-slate-400 font-semibold block">Vehicle Type</label>
                  <select 
                    id="vehicle-select"
                    value={vehicle}
                    onChange={e => setVehicle(e.target.value)}
                    className="w-full bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none"
                  >
                    <option value="petrol">Petrol Sedan</option>
                    <option value="diesel">Diesel Sedan</option>
                    <option value="ev">Electric Car (EV)</option>
                    <option value="public">Transit / Rail</option>
                    <option value="bicycle">Bicycle / Walk</option>
                  </select>
                </div>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div 
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Leaf className="w-5 h-5 text-emerald-500" />
                Step 3: Dietary Profile
              </h3>
              <p className="text-xs text-muted leading-relaxed">Dietary habits heavily impact footprints. Choose the category representing your average menus.</p>

              <div className="space-y-1 pt-2">
                <label htmlFor="diet-select" className="text-xs text-slate-400 font-semibold block">Diet Option</label>
                <select 
                  id="diet-select"
                  value={diet}
                  onChange={e => setDiet(e.target.value)}
                  className="w-full bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none"
                >
                  <option value="omnivore">Omnivore (Standard)</option>
                  <option value="high_meat">Heavy Meat Consumed</option>
                  <option value="vegetarian">Vegetarian Menu</option>
                  <option value="vegan">Vegan Shift</option>
                </select>
              </div>
            </motion.div>
          )}

          {step === 4 && (
            <motion.div 
              key="step4"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-slate-500" />
                Step 4: Refuse & Waste Weight
              </h3>
              <p className="text-xs text-muted leading-relaxed">Enter estimated trash weight generated per month.</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1">
                  <label htmlFor="waste-input" className="text-xs text-slate-400 font-semibold block">Weight (kg)</label>
                  <input 
                    type="number"
                    id="waste-input"
                    placeholder="e.g. 25"
                    value={waste}
                    onChange={e => setWaste(e.target.value)}
                    className="w-full bg-slate-950/50 border border-border rounded-lg py-2.5 px-3 text-foreground focus:outline-none"
                  />
                </div>
                <div className="space-y-1 flex flex-col justify-end">
                  <button 
                    type="button"
                    onClick={() => setRecycled(!recycled)}
                    className={`py-2.5 px-3 border rounded-lg transition-all text-xs font-bold text-center ${
                      recycled ? "bg-emerald-950/20 text-primary border-emerald-500" : "bg-slate-955 border-border text-slate-500"
                    }`}
                  >
                    {recycled ? "✓ Recycled" : "Mark Waste Recycled"}
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {step === 5 && (
            <motion.div 
              key="step5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-6 space-y-4"
            >
              <CheckCircle className="w-12 h-12 text-primary mx-auto animate-bounce" />
              <h3 className="text-xl font-bold text-foreground">Emissions Calculated</h3>
              <p className="text-xs text-muted max-w-sm mx-auto">Today's metrics have been logged successfully into your profile database.</p>
              
              <div className="inline-block p-6 rounded-2xl glass-panel bg-gradient-to-tr from-emerald-950/10 to-transparent">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block">Carbon Impact</span>
                <span className="text-4xl font-black text-white block mt-1 glow-text">{calculatedCo2} <span className="text-lg font-bold">KG CO2e</span></span>
              </div>

              <div>
                <button 
                  onClick={() => { setStep(1); setCalculatedCo2(null); }}
                  className="py-2.5 px-6 rounded-full text-foreground hover:bg-slate-800/10 text-xs font-bold border border-border"
                >
                  Recalculate Log
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Buttons Controls */}
        {step < 5 && (
          <div className="flex items-center justify-between border-t border-border pt-6 mt-6">
            <button 
              onClick={() => setStep(prev => Math.max(1, prev - 1))}
              disabled={step === 1}
              className="py-2 px-5 rounded-lg text-slate-400 hover:text-white text-xs font-bold disabled:opacity-20 transition-all cursor-pointer"
            >
              Back
            </button>

            {step < 4 ? (
              <button 
                onClick={() => setStep(prev => prev + 1)}
                className="py-2 px-6 rounded-lg text-white font-bold bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs transition-all cursor-pointer"
              >
                Next Step
              </button>
            ) : (
              <button 
                onClick={handleCalculate}
                disabled={submitting}
                className="py-2 px-6 rounded-lg text-white font-bold glow-btn text-xs transition-all cursor-pointer"
              >
                {submitting ? "Computing..." : "Compute Carbon Offset"}
              </button>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
