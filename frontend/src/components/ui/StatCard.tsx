type StatCardProps = {
  label: string;
  value: string | number;
};

export function StatCard({ label, value }: StatCardProps) {
  return (
    <article className="metric-card">
      <h4>{label}</h4>
      <p>{value}</p>
    </article>
  );
}
