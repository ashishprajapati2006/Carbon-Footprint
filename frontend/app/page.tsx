"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { 
  Leaf, Car, Zap, Trash2, Bot, Compass, Award, BarChart2, FileText, ArrowRight, Shield, Globe
} from "lucide-react";

export default function LandingPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  } as const;

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 100 } }
  } as const;

  const features = [
    { name: "Habits Calculator", desc: "Instantly track emissions from daily transportation, food choice, and waste habits.", icon: Leaf, color: "text-emerald-500", bg: "bg-emerald-500/10" },
    { name: "Bill OCR Analyzer", desc: "Upload utility invoices. Our Gemini Vision model parses electricity draws and computes logs.", icon: Zap, color: "text-amber-500", bg: "bg-amber-500/10" },
    { name: "Room EcoVision", desc: "Audit appliance energy stars visually via picture captures to target power draws.", icon: FileText, color: "text-blue-500", bg: "bg-blue-500/10" },
    { name: "AI Sustainability Coach", desc: "Chat with your coaching bot regarding customized sustainability targets.", icon: Bot, color: "text-purple-500", bg: "bg-purple-500/10" },
    { name: "Carbon Twin environment", desc: "Simulate offset goals inside a matching virtual carbon twin dashboard.", icon: Compass, color: "text-teal-500", bg: "bg-teal-500/10" },
    { name: "Gamified Challenges", desc: "Participate in daily zero-waste quests, earn XP, and unlock achievement badges.", icon: Award, color: "text-rose-500", bg: "bg-rose-500/10" }
  ];

  return (
    <div className="space-y-16 py-8 md:py-16 overflow-hidden">
      
      {/* Hero Section */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center max-w-3xl mx-auto space-y-6"
      >
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-primary border border-emerald-500/20">
          <Globe className="w-3.5 h-3.5" />
          EcoPilot AI Platform v1.2
        </span>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight leading-tight text-foreground">
          Coordinate Your Path to <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-blue-500 glow-text">Net Zero</span>
        </h1>
        
        <p className="text-muted text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
          Unlock AI-driven carbon calculation, utility bill scanning, visual appliance audits, and conversational coaching to reduce your environmental footprint.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link 
            href="/dashboard"
            className="w-full sm:w-auto py-3 px-8 rounded-full text-white font-bold glow-btn text-xs flex items-center justify-center gap-2"
          >
            Launch Eco Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link 
            href="/calculator"
            className="w-full sm:w-auto py-3 px-8 rounded-full text-foreground bg-slate-900/10 hover:bg-slate-800/10 text-xs font-bold border border-border flex items-center justify-center gap-2"
          >
            Calculate Emissions
          </Link>
        </div>
      </motion.div>

      {/* Grid Features */}
      <div className="space-y-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-foreground">Complete Sustainability Toolset</h2>
          <p className="text-muted text-xs mt-1">Harness advanced tools designed to monitor, model, and minimize emissions.</p>
        </div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feat, idx) => {
            const IconComp = feat.icon;
            return (
              <motion.div 
                key={idx}
                variants={itemVariants}
                className="glass-panel rounded-2xl p-6 space-y-4 flex flex-col justify-between glass-panel-hover"
              >
                <div className="space-y-3">
                  <div className={`w-10 h-10 rounded-xl ${feat.bg} flex items-center justify-center shadow-lg`}>
                    <IconComp className={`w-5 h-5 ${feat.color}`} />
                  </div>
                  <h3 className="font-bold text-foreground text-base">{feat.name}</h3>
                  <p className="text-xs text-muted leading-relaxed">{feat.desc}</p>
                </div>
                
                <Link 
                  href={idx === 1 ? "/bills" : idx === 2 ? "/rooms" : idx === 3 ? "/coach" : idx === 4 ? "/twin" : idx === 5 ? "/challenges" : "/calculator"}
                  className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:text-emerald-400 mt-4 transition-colors"
                >
                  Explore Feature
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </motion.div>
            );
          })}
        </motion.div>
      </div>

      {/* Trust & Security Banner */}
      <div className="glass-panel rounded-3xl p-8 flex flex-col md:flex-row items-center justify-between gap-6 bg-gradient-to-r from-emerald-950/5 to-blue-950/5 border border-border">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h4 className="font-bold text-foreground text-sm">Security & Privacy First</h4>
            <p className="text-xs text-muted mt-0.5">Your invoices, images, and data logs are private and secure. All session interactions are encrypted.</p>
          </div>
        </div>
        
        <div className="text-xs font-semibold text-slate-550 border-l border-border pl-6 hidden md:block">
          <span>Compliant with GHG protocols.</span>
        </div>
      </div>

    </div>
  );
}
