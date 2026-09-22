import PublishStudio from '@/features/publish/components/publish-studio';

export const metadata = {
  title: 'Dashboard: Publish | AURA',
  description: 'Send generated captions to connected Buffer channels.',
};

export default function PublishPage() {
  return <PublishStudio />;
}
