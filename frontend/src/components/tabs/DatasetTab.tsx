import { EmptyState } from "../ui/EmptyState";
import { StatCard } from "../ui/StatCard";
import type { DatasetResponse } from "../../types/app";

type DatasetTabProps = {
  dataset: DatasetResponse | null;
  onRetry: () => void;
  formatCell: (value: unknown) => string;
};

export function DatasetTab({ dataset, onRetry, formatCell }: DatasetTabProps) {
  if (!dataset) {
    return <EmptyState message="No dataset preview loaded yet. Upload a dataset first." actionLabel="Retry Loading Dataset" onAction={onRetry} />;
  }

  const rows = Array.isArray(dataset.rows) ? dataset.rows : [];
  const headers = Array.isArray(dataset.column_names) ? dataset.column_names : [];

  return (
    <div className="dataset-layout">
      <div className="profile-cards">
        <StatCard label="Total Rows" value={Number(dataset.row_count_table ?? 0).toLocaleString()} />
        <StatCard label="Preview Rows" value={Number(dataset.preview_row_count ?? 0).toLocaleString()} />
        <StatCard label="Total Columns" value={headers.length} />
        <StatCard label="Status" value={dataset.truncated ? "Preview mode" : "Full shown"} />
      </div>

      <div className="table-wrap">
        <table className="profile-table">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {row.map((cell, i) => (
                  <td key={`${idx}-${i}`}>{formatCell(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
