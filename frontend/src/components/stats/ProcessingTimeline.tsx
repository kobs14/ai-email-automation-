import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { ProcessingDay } from '../../types/stats';

interface ProcessingTimelineProps {
  data: ProcessingDay[];
}

export function ProcessingTimeline({ data }: ProcessingTimelineProps) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">No data available</p>;
  }

  const formatted = data.map((d) => ({
    ...d,
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }));

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Processing Timeline (7 days)</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="received" stroke="#3b82f6" name="Received" strokeWidth={2} />
          <Line type="monotone" dataKey="processed" stroke="#f59e0b" name="Processed" strokeWidth={2} />
          <Line type="monotone" dataKey="responded" stroke="#22c55e" name="Responded" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
