import LeadReviewPage from '@/features/leads/components/lead-review-page';

export const metadata = {
  title: 'Review Lead | AURA',
  description: 'Review company fit, public evidence, and outreach approval.'
};

export default async function LeadReviewRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LeadReviewPage key={id} leadId={id} />;
}
