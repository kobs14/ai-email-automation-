import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { IntentStat } from '../../types/stats';

interface IntentDistributionProps {
  data: IntentStat[];
}

const INTENT_LABELS: Record<string, string> = {
  quote_request: 'Quote Request',
  booking_request: 'Booking',
  rescheduling: 'Rescheduling',
  complaint: 'Complaint',
  general_inquiry: 'General Inquiry',
  unclassified: 'Unclassified',
};

export function IntentDistribution({ data }: IntentDistributionProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: INTENT_LABELS[d.intent] || d.intent,
  }));

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">No data available</p>;
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Email Intents</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="label" type="category" tick={{ fontSize: 12 }} width={80} />
          <Tooltip />
          <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
