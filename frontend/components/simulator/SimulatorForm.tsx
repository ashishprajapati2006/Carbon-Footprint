"use client";

import React from "react";
import { Compass, Car, Leaf, Zap, RefreshCw } from "lucide-react";

/** Props for the SimulatorForm component. */
interface SimulatorFormProps {
  vehicle: string;
  setVehicle: (val: string) => void;
  diet: string;
  setDiet: (val: string) => void;
  solar: boolean;
  setSolar: (val: boolean) => void;
  simulating: boolean;
  onSubmit: (e: React.FormEvent) => Promise<void>;
}

/**
 * SimulatorForm — Handles user input configurations for the lifestyle footprint simulator.
 */
export function SimulatorForm({
  vehicle,
  setVehicle,
  diet,
  setDiet,
  solar,
  setSolar,
  simulating,
  onSubmit
}: SimulatorFormProps) {
  return (
    <div className="lg:col-span-1 glass-panel rounded-2xl p-6 h-fit">
      <div className="flex items-center gap-2 mb-6">
        <Compass className="w-5 h-5 text-emerald-400" />
        <h3 className="font-bold text-white text-base">Adjust Parameters</h3>
      </div>

      <form onSubmit={onSubmit} className="space-y-5 text-xs">
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
  );
}
