"use client";

import type { Lead, BrandId } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Search } from "lucide-react";
import { useState } from "react";

interface LeadSearchProps {
  filteredLeads: Lead[];
  loading: boolean;
  onSearch: (query: string) => void;
  brandFit: "All" | BrandId;
  setBrandFit: (fit: "All" | BrandId) => void;
}

export function LeadSearch({ filteredLeads, loading, onSearch, brandFit, setBrandFit }: LeadSearchProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery);
    }
  };

  const renderBrandFit = (brand_id: string) => {
    const isJade = brand_id === "jade";
    const dotColor = isJade ? "bg-emerald-500" : "bg-blue-500";
    const textColor = isJade ? "text-emerald-700" : "text-blue-700";
    const bgColor = isJade ? "bg-emerald-50 hover:bg-emerald-50" : "bg-blue-50 hover:bg-blue-50";
    const borderColor = isJade ? "border-emerald-200" : "border-blue-200";
    const fitName = isJade ? "JADE" : "DOCTORSHIELD";

    return (
      <Badge variant="secondary" className={`rounded-full ${bgColor} ${textColor} ${borderColor} border px-3 py-1 shadow-none flex items-center gap-1.5 w-fit font-bold text-[11px] uppercase tracking-wider`}>
        <div className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
        {fitName}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Search and Filters Row */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearch} className="relative w-full max-w-[440px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input 
            id="lead-search-input"
            className="pl-9 bg-white border-slate-200 rounded-xl shadow-sm h-10 text-[14px]"
            placeholder="Search enterprise by name, industry..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>

        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-slate-700 mr-2">Brand Fit:</span>
          {["All", "Jade", "Doctorshield", "Jaguar"].map((brand) => (
            <button
              key={brand}
              onClick={() => setBrandFit(brand === "All" ? "All" : brand.toLowerCase() as BrandId)}
              className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                (brandFit === brand || (brand === "All" && brandFit === "All") || brand.toLowerCase() === brandFit)
                  ? "bg-slate-900 text-white shadow-sm" 
                  : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm"
              }`}
            >
              {brand}
            </button>
          ))}
        </div>
      </div>

      {/* Table Area */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-white border-b border-slate-200">
              <tr>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white">Company</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white">Industry</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white">Country</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white">Brand Fit</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white text-center leading-tight">JA Fit<br/>Score</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white">Status</th>
                <th className="h-12 px-6 text-[12px] font-bold text-slate-500 uppercase tracking-wider bg-white text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLeads.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500 h-48">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <Search className="w-8 h-8 text-slate-300 mb-1" />
                      <p className="text-[14px]">Enter a category and run discovery to find high-value prospects.</p>
                    </div>
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500 h-48">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="w-6 h-6 animate-spin border-2 border-slate-400 border-t-transparent rounded-full mx-auto"></div>
                      <p className="text-[13px] text-slate-500">Orchestrating agentic discovery...</p>
                    </div>
                  </td>
                </tr>
              )}
              {!loading && filteredLeads.map((lead) => (
                <tr key={lead.id} className="bg-white hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900 text-[14px]">{lead.name}</div>
                    <div className="text-[13px] text-slate-500 mt-0.5">{lead.location || lead.country || "Location unavailable"}</div>
                  </td>
                  <td className="px-6 py-4 text-[13px] text-slate-600 font-medium">
                    {lead.category || "Uncategorized"}
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant="outline" className="rounded-full border-slate-200 text-slate-700 font-medium px-3 py-1 shadow-none bg-white text-[12px]">
                      {(lead.location || lead.country || "Singapore").split(',').pop()?.trim() || "Singapore"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    {renderBrandFit(lead.brand_id)}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex flex-col items-center justify-center font-bold">
                      <span className="text-blue-600 text-[16px] leading-none">{lead.fit_score}</span>
                      <span className="text-blue-400 text-[11px] border-t border-blue-100/60 mt-1 pt-0.5 w-8 text-center block">100</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant="secondary" className="rounded-full bg-emerald-50/80 text-emerald-600 hover:bg-emerald-50 font-semibold px-3 py-1 shadow-none border border-emerald-100/50 text-[12px]">
                      {lead.status === "draft_generated" || lead.status === "Draft Generated" ? "Draft Ready" : "Qualified"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link 
                      href={`/dashboard/leads/${lead.id}`}
                      className="font-bold text-slate-900 cursor-pointer hover:text-slate-600 transition-colors text-[13px] inline-flex items-center gap-1"
                    >
                      Inspect Lead <span>&rarr;</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
