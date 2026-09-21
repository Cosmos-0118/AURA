"use client";

import { useState, useEffect } from "react";
import { LeadSearch } from "@/features/leads/lead-search";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserSearch } from "lucide-react"; 
import { searchLeads } from "@/lib/api/client";
import type { Lead, BrandId } from "@/lib/api/types";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ scanned: 184, qualified: 5, highFit: 17, drafts: 26 });

  // Load cached leads on mount
  useEffect(() => {
    const cachedLeads = localStorage.getItem("aura_leads_cache");
    const cachedStats = localStorage.getItem("aura_stats_cache");
    
    if (cachedLeads) {
      try {
        setLeads(JSON.parse(cachedLeads));
      } catch (e) {
        console.error("Failed to parse cached leads", e);
      }
    }
    
    if (cachedStats) {
      try {
        setStats(JSON.parse(cachedStats));
      } catch (e) {
        console.error("Failed to parse cached stats", e);
      }
    }
  }, []);

  const updateStatsAndCache = (newLeads: Lead[]) => {
    setLeads(newLeads);
    localStorage.setItem("aura_leads_cache", JSON.stringify(newLeads));
    
    const scanned = newLeads.length > 0 ? (newLeads.length * 37) + 12 : 184; // Simulated multiplier
    const qualified = newLeads.filter(l => l.status === "Qualified" || l.status === "Draft Generated").length;
    const highFit = newLeads.filter(l => l.fit_score >= 85).length;
    const drafts = newLeads.filter(l => l.status === "Draft Generated" || l.status === "Draft Ready").length;
    
    const newStats = { scanned, qualified, highFit, drafts };
    setStats(newStats);
    localStorage.setItem("aura_stats_cache", JSON.stringify(newStats));
  };

  const handleRunDiscovery = async () => {
    setLoading(true);
    
    try {
      // Run targeted discovery for all 3 brands simultaneously
      const brandQueries = [
        { brand_id: "jade", category: "Jewellery & Luxury Retail", location: "Singapore" },
        { brand_id: "doctorshield", category: "Healthcare Clinics", location: "Singapore" },
        { brand_id: "jaguar", category: "Enterprise Solutions", location: "Singapore" }
      ] as const;

      const results = await Promise.all(
        brandQueries.map(q => searchLeads(q))
      );
      
      const allLeads = results.flat();
      updateStatsAndCache(allLeads);
      
    } catch (err) {
      console.error(err);
      alert("Discovery Agent failed to run. Check console.");
    } finally {
      setLoading(false);
    }
  };
  
  const handleCustomSearch = async (query: string) => {
    setLoading(true);
    const parts = query.split(" in ");
    const category = parts[0] || "Jewellers";
    const location = parts[1] || "Singapore";
    
    try {
      const results = await searchLeads({
        brand_id: "jade",
        category,
        location,
        keywords: query
      });
      // A custom search typically replaces the current view
      updateStatsAndCache(results);
    } catch (err) {
      console.error(err);
      alert("Custom search failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 pb-10">
      {/* Header Area */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-bold tracking-[0.1em] text-slate-500 uppercase mb-2">
            Account Intelligence &bull; Prospect Discovery
          </p>
          <h1 className="text-[34px] font-bold tracking-tight text-slate-900 mb-2 leading-none">
            Lead Intelligence
          </h1>
          <p className="text-slate-500 text-[15px]">
            Find organisations that may need JA Assure's underwriting expertise across ASEAN.
          </p>
        </div>
        <Button 
          onClick={handleRunDiscovery} 
          disabled={loading}
          variant="outline" 
          className="gap-2 font-semibold border-slate-200 text-slate-700 rounded-lg shadow-sm h-9 px-4 text-[13px] disabled:opacity-50"
        >
          {loading ? (
            <div className="w-4 h-4 animate-spin border-2 border-slate-400 border-t-transparent rounded-full" />
          ) : (
            <UserSearch className="w-4 h-4" />
          )}
          Run Discovery Agent
        </Button>
      </div>

      {/* Stats Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Card 1 */}
        <Card className="p-5 border-slate-200 rounded-xl shadow-sm bg-white">
          <p className="text-[13px] font-medium text-slate-600 mb-3">Prospects Scanned</p>
          <div className="text-[32px] font-bold text-slate-900 leading-none">{stats.scanned}</div>
          <p className="text-[12px] text-slate-500 mt-2">High-exposure enterprises</p>
        </Card>
        
        {/* Card 2 */}
        <Card className="p-5 border-slate-200 rounded-xl shadow-sm bg-white">
          <p className="text-[13px] font-medium text-slate-600 mb-3">Qualified Leads</p>
          <div className="text-[32px] font-bold text-emerald-600 leading-none">{stats.qualified}</div>
          <p className="text-[12px] font-semibold text-emerald-600 mt-2">+21% this month</p>
        </Card>

        {/* Card 3 */}
        <Card className="p-5 border-slate-200 rounded-xl shadow-sm bg-white">
          <p className="text-[13px] font-medium text-slate-600 mb-3">High Fit Score (85+)</p>
          <div className="text-[32px] font-bold text-slate-900 leading-none">{stats.highFit}</div>
          <p className="text-[12px] text-slate-500 mt-2">Immediate outreach ready</p>
        </Card>

        {/* Card 4 */}
        <Card className="p-5 border-slate-200 rounded-xl shadow-sm bg-white">
          <p className="text-[13px] font-medium text-slate-600 mb-3">Outreach Drafts</p>
          <div className="text-[32px] font-bold text-slate-900 leading-none">{stats.drafts}</div>
          <p className="text-[12px] text-slate-500 mt-2">Human review required</p>
        </Card>
      </div>

      {/* Search and Table Area */}
      <LeadSearch 
        leads={leads}
        loading={loading}
        onSearch={handleCustomSearch}
      />
    </div>
  );
}
