import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartModel, ChartType, GlobalFilter, SavedDashboard } from "../../types/app";
import { EmptyState } from "../ui/EmptyState";

type ChartsTabProps = {
  charts: ChartModel[];
  allCols: string[];
  chartType: ChartType;
  chartX: string;
  chartY: string;
  chartColor: string;
  chartBins: number;
  chartRowLimit: number;
  globalFilters: GlobalFilter[];
  filterColumn: string;
  filterOperator: GlobalFilter["operator"];
  filterValue: string;
  dashboardName: string;
  dashboards: SavedDashboard[];
  isBusy: boolean;
  setChartType: (v: ChartType) => void;
  setChartX: (v: string) => void;
  setChartY: (v: string) => void;
  setChartColor: (v: string) => void;
  setChartBins: (v: number) => void;
  setChartRowLimit: (v: number) => void;
  setFilterColumn: (v: string) => void;
  setFilterOperator: (v: GlobalFilter["operator"]) => void;
  setFilterValue: (v: string) => void;
  setDashboardName: (v: string) => void;
  onAddFilter: () => void;
  onRemoveFilter: (idx: number) => void;
  onGenerate: () => void;
  onSaveDashboard: () => void;
  onRunDashboard: (id: string) => void;
  onDeleteDashboard: (id: string) => void;
};

export function ChartsTab(props: ChartsTabProps) {
  const {
    charts,
    allCols,
    chartType,
    chartX,
    chartY,
    chartColor,
    chartBins,
    chartRowLimit,
    globalFilters,
    filterColumn,
    filterOperator,
    filterValue,
    dashboardName,
    dashboards,
    isBusy,
    setChartType,
    setChartX,
    setChartY,
    setChartColor,
    setChartBins,
    setChartRowLimit,
    setFilterColumn,
    setFilterOperator,
    setFilterValue,
    setDashboardName,
    onAddFilter,
    onRemoveFilter,
    onGenerate,
    onSaveDashboard,
    onRunDashboard,
    onDeleteDashboard,
  } = props;

  return (
    <div className="chart-builder">
      <p className="insight-meta">Start simple: choose chart type + columns, then click Generate.</p>
      <div className="chart-controls">
        <label className="field">
          <span>Chart Type</span>
          <select value={chartType} onChange={(e) => setChartType(e.target.value as ChartType)}>
            <option value="histogram">Histogram</option>
            <option value="bar">Bar</option>
            <option value="scatter">Scatter</option>
            <option value="line">Line</option>
            <option value="heatmap">Heatmap</option>
            <option value="box">Box</option>
          </select>
        </label>
        <label className="field">
          <span>X Axis / Category</span>
          <select value={chartX} onChange={(e) => setChartX(e.target.value)}>
            <option value="">Select column</option>
            {allCols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Y Axis (if needed)</span>
          <select value={chartY} onChange={(e) => setChartY(e.target.value)}>
            <option value="">Select column</option>
            {allCols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Color Group (optional)</span>
          <select value={chartColor} onChange={(e) => setChartColor(e.target.value)}>
            <option value="">None</option>
            {allCols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Bins (Histogram)</span>
          <input
            type="number"
            min={5}
            max={200}
            value={chartBins}
            onChange={(e) => setChartBins(Number(e.target.value) || 40)}
          />
        </label>
        <label className="field">
          <span>Rows to use</span>
          <input
            type="number"
            min={100}
            max={20000}
            value={chartRowLimit}
            onChange={(e) => setChartRowLimit(Number(e.target.value) || 2000)}
          />
        </label>
        <button className="primary-btn" onClick={onGenerate} disabled={isBusy}>
          Generate Selected Chart
        </button>
      </div>

      <details className="ai-details">
        <summary>Advanced options (optional)</summary>
        <div className="card">
          <h3>Global Filters</h3>
          <div className="chart-controls">
            <label className="field">
              <span>Column</span>
              <select value={filterColumn} onChange={(e) => setFilterColumn(e.target.value)}>
                <option value="">Select column</option>
                {allCols.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Operator</span>
              <select value={filterOperator} onChange={(e) => setFilterOperator(e.target.value as GlobalFilter["operator"])}>
                <option value="=">=</option>
                <option value="!=">!=</option>
                <option value=">">{">"}</option>
                <option value=">=">{">="}</option>
                <option value="<">{"<"}</option>
                <option value="<=">{"<="}</option>
                <option value="contains">contains</option>
                <option value="starts_with">starts_with</option>
                <option value="ends_with">ends_with</option>
              </select>
            </label>
            <label className="field">
              <span>Value</span>
              <input value={filterValue} onChange={(e) => setFilterValue(e.target.value)} placeholder="e.g. Female or 30" />
            </label>
            <button onClick={onAddFilter}>Add Filter</button>
          </div>
          <div className="feature-list">
            {globalFilters.map((f, idx) => (
              <span key={`${f.column}-${f.operator}-${f.value}-${idx}`} className="feature-tag">
                {f.column} {f.operator} {f.value} <button onClick={() => onRemoveFilter(idx)}>x</button>
              </span>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Saved Dashboards</h3>
          <div className="feature-row">
            <input
              value={dashboardName}
              onChange={(e) => setDashboardName(e.target.value)}
              placeholder="Dashboard name"
            />
            <button className="primary-btn" onClick={onSaveDashboard} disabled={isBusy}>
              Save Current View
            </button>
          </div>
          <div className="chat-log">
            {dashboards.length === 0 ? (
              <p className="insight-meta">No saved dashboards yet.</p>
            ) : (
              dashboards.map((d) => (
                <div key={d.id} className="chat-item">
                  <p className="q">{d.name}</p>
                  <p className="insight-meta">Created: {new Date(d.created_at).toLocaleString()}</p>
                  <div className="feature-row">
                    <button onClick={() => onRunDashboard(d.id)}>Run</button>
                    <button onClick={() => onDeleteDashboard(d.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </details>

      <div className="charts-grid">
        {charts.length === 0 ? (
          <EmptyState message='Select chart type + columns, then click "Generate Selected Chart".' />
        ) : (
          charts.map((chart) => (
            <article className="chart-card" key={chart.title}>
              <h3>{chart.title}</h3>
              <RechartsPlot chart={chart} />
              {chart.note ? <p>{chart.note}</p> : null}
            </article>
          ))
        )}
      </div>
    </div>
  );
}

export function RechartsPlot({ chart }: { chart: ChartModel }) {
  if (!chart.data?.length) return <p>No chart data available.</p>;

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        {chart.chart_type === "scatter" ? (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={chart.x_field} />
            <YAxis dataKey={chart.y_field} />
            <Tooltip />
            <Scatter data={chart.data} fill="#4f46e5" />
          </ScatterChart>
        ) : chart.chart_type === "line" ? (
          <LineChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={chart.x_field} />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey={chart.y_field} stroke="#4f46e5" dot={false} />
          </LineChart>
        ) : (
          <BarChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={chart.x_field} />
            <YAxis />
            <Tooltip />
            <Bar dataKey={chart.y_field} fill="#4f46e5" />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
