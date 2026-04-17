import { StatCard } from "../ui/StatCard";
import type { Profile } from "../../types/app";

type ProfileTabProps = {
  profile: Profile | null;
  formatCell: (value: unknown) => string;
};

export function ProfileTab({ profile, formatCell }: ProfileTabProps) {
  if (!profile) {
    return <p>No profile loaded yet. Upload a dataset or click the Profile tab again.</p>;
  }

  const rowCount = Number(profile.row_count_table ?? 0);
  const sampleCount = Number(profile.row_count_profile_sample ?? 0);
  const timeCol = String(profile.time_col_candidate ?? "") || "Not detected";
  const columns = Array.isArray(profile.columns) ? (profile.columns as Array<Record<string, any>>) : [];
  const anomalies =
    profile.anomalies && typeof profile.anomalies === "object"
      ? (profile.anomalies as Record<string, any>)
      : {};
  const highNullColumns = Array.isArray(anomalies.high_null_columns) ? anomalies.high_null_columns : [];
  const outlierCols = anomalies.numeric_outliers && typeof anomalies.numeric_outliers === "object"
    ? Object.entries(anomalies.numeric_outliers as Record<string, number>)
    : [];

  return (
    <div className="profile-layout">
      <div className="profile-cards">
        <StatCard label="Total Rows" value={rowCount.toLocaleString()} />
        <StatCard label="Sampled Rows" value={sampleCount.toLocaleString()} />
        <StatCard label="Columns" value={columns.length} />
        <StatCard label="Time Column" value={timeCol} />
      </div>

      <div className="profile-grid">
        <article className="insight-card">
          <h3>Data Quality Alerts</h3>
          <ul>
            <li>Duplicate rows (sample): {Number(anomalies.duplicate_rows ?? 0).toLocaleString()}</li>
            <li>High-null columns: {highNullColumns.length}</li>
            <li>Outlier columns: {outlierCols.length}</li>
          </ul>
        </article>

        <article className="insight-card">
          <h3>High Null Columns</h3>
          {highNullColumns.length ? (
            <ul>
              {highNullColumns.slice(0, 10).map((name: string) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          ) : (
            <p>No high-null columns detected.</p>
          )}
        </article>

        <article className="insight-card">
          <h3>Top Outlier Columns</h3>
          {outlierCols.length ? (
            <ul>
              {outlierCols
                .sort((a, b) => Number(b[1]) - Number(a[1]))
                .slice(0, 10)
                .map(([name, count]) => (
                  <li key={name}>
                    {name}: {Number(count).toLocaleString()}
                  </li>
                ))}
            </ul>
          ) : (
            <p>No outlier-heavy numeric columns detected.</p>
          )}
        </article>
      </div>

      <div className="table-wrap">
        <table className="profile-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Min</th>
              <th>Max</th>
              <th>Average</th>
              <th>Median</th>
              <th>Std Dev</th>
              <th>Q1</th>
              <th>Q3</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((col) => (
              <tr key={String(col.name)}>
                <td>{String(col.name ?? "-")}</td>
                <td>{formatCell(col.min)}</td>
                <td>{formatCell(col.max)}</td>
                <td>{formatCell(col.mean)}</td>
                <td>{formatCell(col.median)}</td>
                <td>{formatCell(col.std)}</td>
                <td>{formatCell(col.q1)}</td>
                <td>{formatCell(col.q3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
