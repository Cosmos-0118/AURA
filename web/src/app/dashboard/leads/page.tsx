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
  const [brandFit, setBrandFit] = useState<"All" | BrandId>("All");

  // Load cached leads on mount
  useEffect(() => {
    const cachedLeads = localStorage.getItem("aura_leads_cache");
    if (cachedLeads) {
      try {
        setLeads(JSON.parse(cachedLeads));
      } catch (e) {
        console.error("Failed to parse cached leads", e);
      }
    }
  }, []);

  const updateCache = (newLeads: Lead[]) => {
    setLeads(newLeads);
    localStorage.setItem("aura_leads_cache", JSON.stringify(newLeads));
  };

  const handleRunDiscovery = async () => {
    setLoading(true);
    try {
      const brandQueries = [
        { brand_id: "jade", category: "Jewellery & Luxury Retail", location: "Singapore" },
        { brand_id: "doctorshield", category: "Healthcare Clinics", location: "Singapore" },
        { brand_id: "jaguar", category: "Enterprise Solutions", location: "Singapore" }
      ] as const;

      const results = await Promise.all(
        brandQueries.map(q => searchLeads(q))
      );
      
      const allLeads = results.flat();
      updateCache(allLeads);
      // Reset filter to All to show full results
      setBrandFit("All");
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
      updateCache(results);
      setBrandFit("All");
    } catch (err) {
      console.error(err);
      alert("Custom search failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  // Derive filtered leads
  const filteredLeads = leads.filter(lead => {
    if (brandFit === "All") return true;
    return lead.brand_id === brandFit.toLowerCase();
  });

  // Dynamically calculate stats based ONLY on the filtered view!
  const getStats = () => {
    const scanned = filteredLeads.length;
    const qualified = filteredLeads.filter(l => l.status === "Qualified" || l.status === "Draft Generated" || l.status === "draft_generated").length;
    const highFit = filteredLeads.filter(l => l.fit_score >= 85).length;
    const drafts = filteredLeads.filter(l => l.status === "Draft Generated" || l.status === "draft_generated" || l.status === "Draft Ready").length;
    return { scanned, qualified, highFit, drafts };
  };
  
  const stats = getStats();

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
          <p className="text-[12px] font-semibold text-emerald-600 mt-2">Target profiles</p>
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
        filteredLeads={filteredLeads}
        loading={loading}
        onSearch={handleCustomSearch}
        brandFit={brandFit}
        setBrandFit={setBrandFit}
      />
    </div>
  );
}
