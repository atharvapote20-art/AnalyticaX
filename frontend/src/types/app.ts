export type Profile = Record<string, unknown>;

export type InsightItem = {
  message: string;
  category: "insight" | "risk" | "recommendation" | string;
  severity: "high" | "medium" | "low" | string;
  confidence: number;
  why: string;
  action: string;
};

export type Insights = {
  insights: InsightItem[];
  data_quality_risks: InsightItem[];
  recommendations: InsightItem[];
};

export type ChartPoint = Record<string, unknown>;

export type ChartModel = {
  title: string;
  chart_type: "histogram" | "bar" | "scatter" | "line";
  x_field: string;
  y_field: string;
  data: ChartPoint[];
  note?: string;
};

export type ChartResponse = {
  charts: ChartModel[];
};

export type DatasetResponse = {
  row_count_table: number;
  preview_row_count: number;
  column_names: string[];
  rows: unknown[][];
  columns: Array<Record<string, any>>;
  truncated: boolean;
};

export type ChartType = "histogram" | "bar" | "scatter" | "line" | "heatmap" | "box";

export type ColumnMeta = { name: string; dtype: string };

export type GlobalFilter = {
  column: string;
  operator: "=" | "!=" | ">" | ">=" | "<" | "<=" | "contains" | "starts_with" | "ends_with";
  value: string;
};

export type SavedDashboard = {
  id: string;
  name: string;
  created_at: string;
  config: {
    chart_type: ChartType;
    x: string | null;
    y: string | null;
    color: string | null;
    bins: number;
    row_limit: number;
    filters: GlobalFilter[];
  };
};

export type ChatResponse = {
  reply: string;
  confidence?: number;
  explanation?: string;
  generated_sql?: string;
  mode?: "ai" | "rule_based" | string;
  tool_trace?: Array<{ query: string; truncated?: boolean; error?: string }>;
  result?: { columns: string[]; rows: unknown[][]; truncated: boolean };
};

export type ChatEntry = { question: string; answer: ChatResponse };
