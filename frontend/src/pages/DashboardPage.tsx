import { Mail, MessageSquare, Clock, Calendar } from 'lucide-react';
import { useOverview, useIntents, useProcessingTimeline } from '../hooks/useStats';
import { StatCard } from '../components/stats/StatCard';
import { EmailStatusChart } from '../components/stats/EmailStatusChart';
import { IntentDistribution } from '../components/stats/IntentDistribution';
import { ProcessingTimeline } from '../components/stats/ProcessingTimeline';
import { PageLoader } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';

export function DashboardPage() {
  const { data: overview, isLoading: loadingOverview, error: overviewError, refetch: refetchOverview } = useOverview();
  const { data: intents, isLoading: loadingIntents } = useIntents();
  const { data: timeline, isLoading: loadingTimeline } = useProcessingTimeline(7);

  if (loadingOverview) return <PageLoader />;
  if (overviewError) return <ErrorAlert message="Failed to load dashboard data" onRetry={refetchOverview} />;

  const totalEmails = overview
    ? Object.values(overview.email_counts).reduce((sum, n) => sum + n, 0)
    : 0;
  const pendingDrafts = overview?.response_counts?.draft ?? 0;
  const sentResponses = overview?.response_counts?.sent ?? 0;
  const upcomingEvents = overview?.upcoming_events ?? 0;

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Emails"
          value={totalEmails}
          icon={<Mail className="w-6 h-6" />}
          color="text-blue-600"
        />
        <StatCard
          title="Pending Drafts"
          value={pendingDrafts}
          icon={<Clock className="w-6 h-6" />}
          color="text-yellow-600"
          subtitle="Awaiting review"
        />
        <StatCard
          title="Sent Responses"
          value={sentResponses}
          icon={<MessageSquare className="w-6 h-6" />}
          color="text-green-600"
        />
        <StatCard
          title="Upcoming Events"
          value={upcomingEvents}
          icon={<Calendar className="w-6 h-6" />}
          color="text-purple-600"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {overview && <EmailStatusChart data={overview.email_counts} />}
        {!loadingIntents && intents && <IntentDistribution data={intents.items} />}
      </div>

      {/* Timeline */}
      {!loadingTimeline && timeline && <ProcessingTimeline data={timeline.items} />}
    </div>
  );
}
