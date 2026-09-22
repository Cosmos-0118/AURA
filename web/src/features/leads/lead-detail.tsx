"use client";

import { useState, useEffect } from "react";
import { generateLeadOutreach } from "@/lib/api/client";
import type { Lead } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Building2, Globe, MapPin, Phone, Mail, CheckCircle2, Sparkles, ExternalLink, Activity, Target } from "lucide-react";

export function LeadDetail({ leadId }: { leadId: string }) {
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Fetch lead details. In a real app we'd have a specific GET endpoint.
    import("@/lib/api/client").then(({ listLeads }) => {
      listLeads().then((leads) => {
        const found = leads.find((l) => l.id === leadId);
        setLead(found || null);
        setLoading(false);
      }).catch((err) => {
        console.error(err);
        setLoading(false);
      });
    });
  }, [leadId]);

  const handleGenerateOutreach = async () => {
    if (!lead) return;
    setGenerating(true);
    try {
      const res = await generateLeadOutreach(lead.id, {
        brand_id: lead.brand_id,
        lead_id: lead.id,
      });
      toast.success(res.message);
      // Wait a moment and redirect to review queue
      setTimeout(() => {
        router.push("/dashboard/review");
      }, 1500);
    } catch (err: any) {
      toast.error(err.message || "Failed to generate outreach");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <Activity className="w-8 h-8 animate-spin text-primary mb-4" />
        <p>Loading intelligence data...</p>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <Target className="w-12 h-12 mb-4 opacity-50" />
        <h2 className="text-xl font-semibold">Lead Not Found</h2>
        <p className="mt-2 text-sm">The requested prospect profile could not be located.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Main Left Column */}
      <div className="lg:col-span-2 space-y-8">
        
        {/* Profile Card */}
        <Card className="shadow-sm border-slate-200/60 bg-white overflow-hidden">
          <div className="h-32 bg-gradient-to-r from-slate-100 to-slate-50 w-full border-b border-slate-100 relative">
            <div className="absolute -bottom-8 left-6 w-20 h-20 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center">
              <Building2 className="w-10 h-10 text-slate-300" />
            </div>
            <div className="absolute top-4 right-4">
              <Badge variant="outline" className="bg-white/80 backdrop-blur-sm text-slate-600 font-medium">
                {lead.status === "Draft Generated" ? "Draft Ready" : lead.status}
              </Badge>
            </div>
          </div>
          <div className="pt-12 pb-6 px-6">
            <h2 className="text-2xl font-bold text-slate-900">{lead.name}</h2>
            <div className="flex flex-wrap gap-3 mt-3 text-sm text-muted-foreground font-medium">
              <div className="flex items-center gap-1">
                <Target className="w-4 h-4 text-slate-400" />
                {lead.category}
              </div>
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4 text-slate-400" />
                {lead.location}
              </div>
              {lead.url ? (
                <a href={lead.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-primary hover:underline transition-all">
                  <Globe className="w-4 h-4" />
                  {new URL(lead.url).hostname}
                </a>
              ) : (
                <div className="flex items-center gap-1 text-slate-400">
                  <Globe className="w-4 h-4" />
                  Official website: Not available
                </div>
              )}
            </div>
            
            <p className="mt-6 text-slate-600 leading-relaxed text-sm">
              {lead.description}
            </p>
          </div>
        </Card>

        {/* Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="shadow-sm border-slate-200/60 bg-white">
            <CardHeader className="pb-3 border-b border-slate-100">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                Contact Intelligence
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-sm">
              <div className="flex items-start gap-3">
                <Phone className="w-4 h-4 text-slate-400 mt-0.5" />
                <div>
                  <p className="font-medium text-slate-700">Phone</p>
                  <p className="text-muted-foreground">{lead.phone || "Not available"}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Mail className="w-4 h-4 text-slate-400 mt-0.5" />
                <div>
                  <p className="font-medium text-slate-700">Public Email</p>
                  <p className="text-muted-foreground">{lead.public_email || "Not available"}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <ExternalLink className="w-4 h-4 text-slate-400 mt-0.5" />
                <div>
                  <p className="font-medium text-slate-700">Social Links</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {lead.social_links && lead.social_links.length > 0 ? (
                      lead.social_links.map((link, i) => (
                        <a key={i} href={link} target="_blank" className="text-primary hover:underline">Link {i+1}</a>
                      ))
                    ) : (
                      <span className="text-muted-foreground">None found</span>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-200/60 bg-white">
            <CardHeader className="pb-3 border-b border-slate-100">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-500" />
                Research Evidence
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-sm">
              <div>
                <p className="font-medium text-slate-700">Identified Services</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {lead.services && lead.services.length > 0 ? lead.services.map((svc, i) => (
                    <Badge key={i} variant="secondary" className="font-normal text-xs">{svc}</Badge>
                  )) : (
                    <span className="text-muted-foreground">None identified</span>
                  )}
                </div>
              </div>
              <div className="pt-2 border-t border-slate-50">
                <p className="font-medium text-slate-700">Research Verified</p>
                <p className="text-muted-foreground mt-1">
                  {lead.last_verified_at 
                    ? new Date(lead.last_verified_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
                    : "Not verified"}
                </p>
              </div>
              <div className="pt-2 border-t border-slate-50">
                <p className="font-medium text-slate-700">Data Source</p>
                <p className="text-muted-foreground mt-1">{lead.source}</p>
                {lead.source_url && (
                  <a href={lead.source_url} target="_blank" rel="noreferrer" className="text-primary hover:underline text-xs mt-1 inline-block">
                    View Source Reference &rarr;
                  </a>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Right Column (Action/Fit) */}
      <div className="space-y-6">
        
        {/* Fit Analysis Card */}
        <Card className={`shadow-sm border ${lead.fit_score >= 80 ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-white'}`}>
          <CardContent className="p-6">
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">JA Fit Score</p>
                <div className={`text-5xl font-bold ${lead.fit_score >= 80 ? 'text-emerald-600' : 'text-slate-700'}`}>
                  {lead.fit_score}
                </div>
              </div>
              <Badge variant="outline" className={lead.fit_score >= 80 ? "bg-emerald-100 text-emerald-800 border-emerald-200" : ""}>
                {lead.fit_score >= 80 ? "HIGH PRIORITY" : lead.fit_score >= 50 ? "MEDIUM PRIORITY" : "LOW PRIORITY"}
              </Badge>
              <div className="text-sm text-slate-600 pt-4 border-t border-slate-200/60 w-full text-left">
                <p className="font-medium text-slate-800 mb-3 text-center">Score Breakdown:</p>
                <ul className="space-y-2">
                  {lead.fit_reasons && lead.fit_reasons.length > 0 ? (
                    lead.fit_reasons.map((reason, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                        <span className="leading-tight">{reason}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-muted-foreground text-center text-xs">Legacy score ({lead.why})</li>
                  )}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Card */}
        <Card className="shadow-sm border-slate-200/60 bg-slate-900 text-slate-50">
          <CardContent className="p-6 flex flex-col items-center text-center space-y-4">
            <Sparkles className="w-8 h-8 text-amber-400" />
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Agentic Outreach</h3>
              <p className="text-sm text-slate-300">
                Generate a highly personalized message using AI context analysis.
              </p>
            </div>
            <Button 
              onClick={handleGenerateOutreach} 
              disabled={generating || lead.status === "Draft Generated"}
              className="w-full bg-white text-slate-900 hover:bg-slate-100 font-semibold gap-2 mt-2 h-11"
            >
              {generating ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  Generating Draft...
                </>
              ) : lead.status === "Draft Generated" ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Draft Ready in Review
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Outreach
                </>
              )}
            </Button>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
