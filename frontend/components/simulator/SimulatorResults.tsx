"use client";

import React from "react";
import { motion } from "framer-motion";
import { Sparkles, CheckSquare } from "lucide-react";

/** Result returned by the carbon lifestyle simulation endpoint. */
interface SimulationResult {
  original_co2_kg: number;
  projected_co2_kg: number;
  potential_saving_percentage: number;
  recommendations: string[];
}

/** Props for the SimulatorResults component. */
interface SimulatorResultsProps {
  result: SimulationResult | null;
}

/**
 * SimulatorResults — Renders the projection numbers and checklist recommendation cards.
 */
export function SimulatorResults({ result }: SimulatorResultsProps) {
  if (!result) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="glass-panel rounded-2xl p-16 flex flex-col items-center justify-center text-center space-y-4 h-full min-h-[300px]"
      >
        <Sparkles className="w-10 h-10 text-emerald-400/50 animate-pulse" />
        <p className="text-sm font-bold text-slate-350">Simulation Results Sandbox</p>
        <p className="text-xs text-slate-500 max-w-sm">
          Adjust lifestyle inputs on the side panel and trigger simulation models to forecast emissions reductions.
        </p>
      </motion.div>
    );
  }

  return (
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
  );
}
