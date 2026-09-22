import { LeadDetail } from "@/features/leads/lead-detail";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Link 
          href="/dashboard/leads" 
          className="p-2 -ml-2 rounded-full hover:bg-slate-100 text-slate-500 transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div>
          <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            Account Intelligence &bull; Lead Profile
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Lead Details</h1>
        </div>
      </div>
      <LeadDetail leadId={params.id} />
    </div>
  );
}
