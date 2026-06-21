"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Send, Bot, User, Sparkles, Trash2, Plus, 
  Calendar, MessageSquare, AlertCircle, Leaf,
  Menu, X
} from "lucide-react";
import { getBackendUrl, getAuthHeaders } from "@/services/api";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

export default function CoachChat() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const backendUrl = getBackendUrl("/coach");

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${backendUrl}/sessions`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        if (data.length > 0 && !activeSession) {
          loadSession(data[0]._id); // Load latest session by default
        }
      } else {
        throw new Error("Failed to fetch sessions");
      }
    } catch (err) {
      console.warn("Backend offline. Setting up local mock chat sessions.");
      const mockSessions = [
        {
          _id: "mock-1",
          session_title: "Mock Conversation Thread",
          updated_at: new Date().toISOString()
        }
      ];
      setSessions(mockSessions);
      setActiveSession(mockSessions[0]);
      setMessages([
        {
          role: "assistant",
          content: "Hello! I am your EcoPilot AI assistant. How can I help you reduce your carbon footprint or explain environmental parameters today?",
          timestamp: new Date().toISOString()
        }
      ]);
    }
  };

  const loadSession = async (sessionId: string) => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${backendUrl}/sessions/${sessionId}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setActiveSession(data);
        setMessages(data.messages || []);
      } else {
        throw new Error("Failed to load session details");
      }
    } catch (err) {
      console.warn("Failed to load details from backend. Running mock hydration.");
    }
    setLoadingHistory(false);
  };

  const createNewSession = async (): Promise<any | null> => {
    setCreatingSession(true);
    try {
      const res = await fetch(`${backendUrl}/sessions`, {
        method: "POST",
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const newSess = await res.json();
        setSessions(prev => [newSess, ...prev]);
        setActiveSession(newSess);
        setMessages(newSess.messages || []);
        return newSess;
      } else {
        throw new Error("Failed to create thread");
      }
    } catch (err) {
      // Mock new session fallback
      const mockId = `mock-${Date.now()}`;
      const mockNew = {
        _id: mockId,
        session_title: `EcoPilot Chat - ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        updated_at: new Date().toISOString()
      };
      setSessions(prev => [mockNew, ...prev]);
      setActiveSession(mockNew);
      setMessages([
        {
          role: "assistant",
          content: "Hello! I am your EcoPilot AI coach. Ask me questions like: \n- *What is my carbon footprint?*\n- *How can I save electricity?*\n- *Recommend sustainable diets.*",
          timestamp: new Date().toISOString()
        }
      ]);
      return mockNew;
    } finally {
      setCreatingSession(false);
    }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${backendUrl}/sessions/${sessionId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      setSessions(prev => prev.filter(s => s._id !== sessionId));
      if (activeSession?._id === sessionId) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch (err) {
      setSessions(prev => prev.filter(s => s._id !== sessionId));
      if (activeSession?._id === sessionId) {
        setActiveSession(null);
        setMessages([]);
      }
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    let sessId = activeSession?._id;
    
    // Auto-create a session if none is active, then continue sending
    if (!sessId) {
      const newSess = await createNewSession();
      if (!newSess?._id) return; // bail if creation failed
      sessId = newSess._id;
    }

    const userText = inputValue;
    setInputValue("");
    setStreaming(true);

    // Append user message immediately
    const userMsg = {
      role: "user",
      content: userText,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);

    // ── Mock session: reply locally without hitting the backend ─────────
    if (sessId.startsWith("mock-")) {
      const query = userText.toLowerCase();
      let reply = "I can guide you on solar panels installation, food carbon offsets, or transport swaps. Try adjusting parameters on the Simulator!";
      if (["transport", "car", "travel", "commut", "bus", "train", "vehicl", "bike", "cycle"].some(w => query.includes(w))) {
        reply = "Swapping single-occupancy petrol commuting for public transport or electric vehicles reduces transit carbon footprints by approximately **75%**. Biking or walking for trips under **3 km** makes a huge difference!";
      } else if (["diet", "food", "meat", "vegetar", "vegan", "grocer", "plant-based", "eat"].some(w => query.includes(w))) {
        reply = "Transitioning to a plant-based (vegan/vegetarian) diet offsets carbon footprints by **2-4 kg CO2 daily**. Consider starting with *Meatless Mondays*:\n\n1. **Swap beef for beans** in tacos.\n2. **Use almond or oat milk** instead of dairy.\n3. **Buy seasonal local foods** to lower transport loads.";
      } else if (["bill", "elect", "power", "energ", "kwh", "solar", "light", "heat"].some(w => query.includes(w))) {
        reply = "You can reduce residential electricity draw by:\n\n- Swapping lights for **9W LEDs**.\n- Adjusting thermostat settings by **1-2 degrees**.\n- Unplugging standby power draws when idle.";
      } else if (["water", "shower", "leak", "tap", "drip", "wash"].some(w => query.includes(w))) {
        reply = "💧 Heating water accounts for ~18% of home energy use. Take shorter showers, fix leaky taps (a drip wastes 9 litres/day), and wash clothes in cold water.";
      } else if (["waste", "recycl", "compost", "trash", "landfill", "bin"].some(w => query.includes(w))) {
        reply = "♻️ Composting organic waste and sorting recyclables can divert 60–70% of household waste from landfill. Landfill methane is 28× more potent than CO₂, so every bag you compost makes a real difference.";
      }

      // Simulate streaming word-by-word
      setMessages(prev => [...prev, { role: "assistant", content: "", timestamp: new Date().toISOString() }]);
      const words = reply.split(" ");
      let built = "";
      for (let i = 0; i < words.length; i += 2) {
        built += (i > 0 ? " " : "") + words.slice(i, i + 2).join(" ");
        const snapshot = built;
        setMessages(prev => {
          const list = [...prev];
          list[list.length - 1] = { ...list[list.length - 1], content: snapshot };
          return list;
        });
        await new Promise(r => setTimeout(r, 50));
      }
      setStreaming(false);
      return;
    }

    // ── Real backend streaming ───────────────────────────────────────────
    try {
      // Call streaming endpoint
      const response = await fetch(`${backendUrl}/sessions/${sessId}/message/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({ message: userText })
      });

      if (!response.ok) throw new Error(`Streaming call failed: ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader object");

      // Append blank assistant bubble
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString()
        }
      ]);

      let done = false;
      let accumulatedText = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          let chunk = decoder.decode(value, { stream: !done });
          // Strip SSE "data: " prefix if present
          chunk = chunk.replace(/^data:\s*/gm, "").replace(/\n\n$/, "");
          accumulatedText += chunk;
          
          setMessages(prev => {
            const list = [...prev];
            if (list.length > 0) {
              const lastIdx = list.length - 1;
              list[lastIdx] = {
                ...list[lastIdx],
                content: accumulatedText
              };
            }
            return list;
          });
        }
      }
      
      // Update sidebar session details (to display latest title timestamp)
      fetchSessions();
    } catch (err) {
      // Backend offline fallback simulation
      const query = userText.toLowerCase();
      let reply = "I can guide you on solar panels installation, food carbon offsets, or transport swaps. Try adjusting parameters on the Simulator!";
      
      if (["transport", "car", "travel", "commut", "bus", "train", "vehicl", "bike", "cycle"].some(w => query.includes(w))) {
        reply = "Swapping single-occupancy petrol commuting for public transport or electric vehicles reduces transit carbon footprints by approximately **75%**. Biking or walking for trips under **3 km** makes a huge difference!";
      } else if (["diet", "food", "meat", "vegetar", "vegan", "grocer", "plant-based", "eat"].some(w => query.includes(w))) {
        reply = "Transitioning to a plant-based (vegan/vegetarian) diet offsets carbon footprints by **2-4 kg CO2 daily**. Consider starting with *Meatless Mondays*:\n\n1. **Swap beef for beans** in tacos.\n2. **Use almond or oat milk** instead of dairy.\n3. **Buy seasonal local foods** to lower transport loads.";
      } else if (["bill", "elect", "power", "energ", "kwh", "solar", "light", "heat"].some(w => query.includes(w))) {
        reply = "You can reduce residential electricity draw by:\n\n- Swapping lights for **9W LEDs**.\n- Adjusting thermostat settings by **1-2 degrees**.\n- Unplugging standby power draws when idle.";
      }

      const mockAssistantMsg = {
        role: "assistant",
        content: reply,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, mockAssistantMsg]);
    }
    setStreaming(false);
  };



  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 md:px-6 py-6 flex flex-col h-full">
      
      {/* Title Header */}
      <div className="border-b border-slate-800/85 pb-4 shrink-0">
        <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider bg-emerald-950/30 px-3 py-1 rounded-full w-fit">
          <Leaf className="w-3.5 h-3.5" />
          EcoPilot Assistant
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight mt-2">AI Sustainability Assistant</h1>
        <p className="text-slate-400 text-xs md:text-sm mt-1">Get streaming sustainability advice, footprint breakdowns, and recommendations backed by Gemini.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-[calc(100vh-240px)] lg:h-[calc(100vh-280px)] min-h-[450px] lg:min-h-[500px] relative">
        
        {/* Sidebar: Chat History Thread manager (Drawer overlay on mobile, 4 columns on desktop) */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSidebarOpen(false)}
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-xs z-40 lg:hidden"
            />
          )}
        </AnimatePresence>

        <div 
          className={`
            fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 lg:z-0 lg:w-auto lg:max-w-none lg:inset-auto lg:transform-none lg:transition-none
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
            lg:col-span-4 h-full flex flex-col justify-between glass-panel rounded-r-2xl lg:rounded-2xl p-4 overflow-hidden border-r border-slate-800/80 lg:border-slate-800/80 bg-slate-950 lg:bg-transparent
          `}
        >
          <div className="space-y-4 flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between border-b border-slate-850 pb-3">
              <span className="font-extrabold text-white text-xs uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                Conversations
              </span>
              <div className="flex items-center gap-1.5">
                <button 
                  onClick={async () => {
                    await createNewSession();
                    setSidebarOpen(false);
                  }}
                  disabled={creatingSession || streaming}
                  className="p-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-950/80 border border-emerald-500/20 hover:border-emerald-500/40 text-emerald-400 transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creatingSession ? (
                    <span className="w-3.5 h-3.5 border border-t-emerald-400 border-r-transparent rounded-full animate-spin" />
                  ) : (
                    <Plus className="w-3.5 h-3.5" />
                  )}
                  New
                </button>
                <button 
                  onClick={() => setSidebarOpen(false)}
                  className="lg:hidden p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {sessions.map(s => (
                <div 
                  key={s._id}
                  onClick={() => { 
                    if (!streaming && !loadingHistory) {
                      loadSession(s._id); 
                      setSidebarOpen(false);
                    }
                  }}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                    activeSession?._id === s._id 
                      ? "border-emerald-500/35 bg-emerald-950/15" 
                      : "border-slate-850 bg-slate-950/20 hover:bg-slate-950/50 hover:border-slate-700/60"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`p-1.5 rounded-lg ${activeSession?._id === s._id ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-900 text-slate-500"}`}>
                      <Sparkles className="w-3.5 h-3.5" />
                    </div>
                    <div className="text-left min-w-0">
                      <span className="font-semibold text-xs text-white block truncate leading-tight">
                        {s.session_title}
                      </span>
                      <span className="text-[9px] text-slate-500 block mt-1 flex items-center gap-1">
                        <Calendar className="w-3 h-3 shrink-0" />
                        {s.updated_at ? new Date(s.updated_at).toLocaleDateString([], { month: "short", day: "numeric" }) : ""}
                      </span>
                    </div>
                  </div>
                  
                  <button 
                    onClick={(e) => deleteSession(s._id, e)}
                    disabled={streaming}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-500 hover:text-rose-450 hover:bg-slate-900 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}

              {sessions.length === 0 && (
                <div className="text-center py-10 text-slate-500 text-xs font-semibold">
                  No conversations yet. Click "New Thread" to start.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Panel: Interactive Chat Screen (8 Columns) */}
        <div className="lg:col-span-8 h-full flex flex-col justify-between glass-panel rounded-2xl overflow-hidden border-slate-800/80">
          
          {/* Header */}
          <div className="px-4 md:px-6 py-4 border-b border-slate-850 bg-slate-950/30 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              {/* Menu Toggle Button for mobile */}
              <button 
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-850 transition-colors cursor-pointer mr-1 shrink-0"
              >
                <Menu className="w-4.5 h-4.5" />
              </button>

              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center text-emerald-450 shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h3 className="font-bold text-white text-sm truncate">
                  {activeSession ? activeSession.session_title : "No Thread Selected"}
                </h3>
                <span className="text-[9px] text-emerald-400 font-extrabold tracking-wider uppercase block mt-0.5">
                  {streaming ? "Streaming Gemini Tokens..." : "AI Ready to Assist"}
                </span>
              </div>
            </div>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 md:space-y-6 bg-slate-950/5">
            {loadingHistory ? (
              <div className="h-full flex items-center justify-center flex-col space-y-3">
                <div className="w-7 h-7 border-2 border-t-emerald-500 border-r-transparent border-slate-800 rounded-full animate-spin" />
                <span className="text-xs text-slate-500 font-semibold">Retrieving session logs...</span>
              </div>
            ) : (
              <>
                {messages.map((msg, index) => {
                  const isUser = msg.role === "user";
                  return (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      key={index}
                      className={`flex items-start gap-2.5 md:gap-3.5 max-w-[90%] md:max-w-[85%] ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                    >
                      <div className={`w-8 h-8 md:w-8.5 md:h-8.5 rounded-full flex items-center justify-center shrink-0 border ${
                        isUser 
                          ? "bg-blue-600/10 border-blue-500/15 text-blue-400" 
                          : "bg-emerald-600/10 border-emerald-500/15 text-emerald-405"
                      }`}>
                        {isUser ? <User className="w-4 h-4 md:w-4.5 md:h-4.5" /> : <Bot className="w-4 h-4 md:w-4.5 md:h-4.5" />}
                      </div>
                      
                      <div className={`p-3 md:p-4 rounded-2xl border text-xs shadow-md ${
                        isUser 
                          ? "bg-gradient-to-br from-blue-600 to-blue-700 text-white border-blue-600 rounded-tr-none" 
                          : "glass-panel text-slate-200 border-slate-800/70 rounded-tl-none bg-slate-950/20"
                      }`}>
                        {isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        ) : (
                          <div className="space-y-1">
                            <MarkdownRenderer content={msg.content} />
                          </div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}

                {/* Bouncing Dots Stream Typing Loader */}
                {streaming && messages[messages.length - 1]?.content === "" && (
                  <div className="flex items-start gap-2.5 md:gap-3.5 mr-auto">
                    <div className="w-8 h-8 md:w-8.5 md:h-8.5 rounded-full bg-emerald-600/10 border border-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0">
                      <Bot className="w-4 h-4 md:w-4.5 md:h-4.5" />
                    </div>
                    <div className="p-3 md:p-4 rounded-2xl glass-panel text-slate-400 border-slate-850 rounded-tl-none bg-slate-950/20 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Bottom Form input */}
          <div className="p-3 md:p-4 border-t border-slate-850 bg-slate-950/30">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input 
                type="text"
                placeholder={activeSession ? "Ask anything (e.g., 'How do I save water?')" : "Start a new conversation thread..."}
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                disabled={streaming || creatingSession}
                className="flex-1 bg-slate-950 border border-slate-850 rounded-xl px-3 py-2.5 md:px-4 md:py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-45"
              />
              <button 
                type="submit"
                disabled={streaming || creatingSession || !inputValue.trim()}
                className="w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:opacity-40 disabled:shadow-none text-white shadow-lg shadow-emerald-600/20 transition-all cursor-pointer shrink-0"
              >
                <Send className="w-4.5 h-4.5" />
              </button>
            </form>
          </div>

        </div>

      </div>
    </div>
  );
}
