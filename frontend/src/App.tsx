import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { BarChart3, Database, Lightbulb, Loader2, MessageSquareText, Upload } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "./lib/api";
import type {
  ChartResponse,
  ChartType,
  ChatEntry,
  ChatResponse,
  ColumnMeta,
  DatasetResponse,
  GlobalFilter,
  Insights,
  Profile,
  SavedDashboard,
} from "./types/app";
import { PageHeader } from "./components/ui/PageHeader";
import { SectionCard } from "./components/ui/SectionCard";
import { DatasetTab } from "./components/tabs/DatasetTab";
import { ProfileTab } from "./components/tabs/ProfileTab";
import { InsightsTab } from "./components/tabs/InsightsTab";
import { ChartsTab } from "./components/tabs/ChartsTab";
import { ChatTab } from "./components/tabs/ChatTab";

function App() {
  const [theme, setTheme] = useState<"midnight" | "graphite">(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem("analyticax-theme") : null;
    return saved === "graphite" ? "graphite" : "midnight";
  });
  const [activeTab, setActiveTab] = useState<"dataset" | "profile" | "insights" | "charts" | "chat">("dataset");
  const [file, setFile] = useState<File | null>(null);
  const [filePath, setFilePath] = useState("");
  const [status, setStatus] = useState("Upload a file to begin.");
  const [isBusy, setIsBusy] = useState(false);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [charts, setCharts] = useState<ChartResponse["charts"]>([]);
  const [datasetView, setDatasetView] = useState<DatasetResponse | null>(null);
  const [chartType, setChartType] = useState<ChartType>("histogram");
  const [chartX, setChartX] = useState("");
  const [chartY, setChartY] = useState("");
  const [chartColor, setChartColor] = useState("");
  const [chartBins, setChartBins] = useState(40);
  const [chartRowLimit, setChartRowLimit] = useState(2000);
  const [globalFilters, setGlobalFilters] = useState<GlobalFilter[]>([]);
  const [filterColumn, setFilterColumn] = useState("");
  const [filterOperator, setFilterOperator] = useState<GlobalFilter["operator"]>("=");
  const [filterValue, setFilterValue] = useState("");
  const [dashboardName, setDashboardName] = useState("");
  const [dashboards, setDashboards] = useState<SavedDashboard[]>([]);
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatLog, setChatLog] = useState<ChatEntry[]>([]);

  const tabs = useMemo(
    () => [
      { id: "dataset", label: "Dataset", icon: Database },
      { id: "profile", label: "Profile", icon: BarChart3 },
      { id: "insights", label: "Insights", icon: Lightbulb },
      { id: "charts", label: "Charts", icon: BarChart3 },
      { id: "chat", label: "Ask Data", icon: MessageSquareText },
    ] as const,
    [],
  );

  const heroStats = useMemo(
    () => [
      {
        label: "Rows",
        value: Number(datasetView?.row_count_table ?? 0).toLocaleString(),
      },
      {
        label: "Columns",
        value: String(datasetView?.column_names?.length ?? 0),
      },
      {
        label: "Insights",
        value: String(
          (insights?.insights?.length ?? 0) +
            (insights?.data_quality_risks?.length ?? 0) +
            (insights?.recommendations?.length ?? 0),
        ),
      },
      {
        label: "Charts",
        value: String(charts.length),
      },
    ],
    [datasetView, insights, charts],
  );

  const uploadMultipart = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("/datasets/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setProfile(response.data.profile ?? null);
    setStatus(`Uploaded "${response.data.filename}" successfully.`);
  };

  const uploadByPath = async () => {
    const trimmedPath = filePath.trim();
    if (!trimmedPath) return;
    const response = await api.post("/datasets/upload-by-path", { path: trimmedPath });
    setProfile(response.data.profile ?? null);
    setStatus(`Loaded "${response.data.filename}" from local path.`);
  };

  const fetchProfile = async () => {
    const response = await api.get("/datasets/profile");
    setProfile(response.data);
    setActiveTab("profile");
    setStatus("Profile loaded.");
  };

  const fetchDataset = async () => {
    const response = await api.get<DatasetResponse>("/datasets/dataset");
    setDatasetView(response.data);
    setActiveTab("dataset");
    setStatus("Dataset preview loaded.");
  };

  const fetchInsights = async () => {
    const response = await api.post("/datasets/insights");
    setInsights(response.data);
    setActiveTab("insights");
    setStatus("Insights generated.");
  };

  const fetchCustomChart = async () => {
    const response = await api.post<ChartResponse>("/datasets/charts/custom", {
      chart_type: chartType,
      x: chartX || null,
      y: chartY || null,
      color: chartColor || null,
      bins: chartBins,
      row_limit: chartRowLimit,
      filters: globalFilters,
    });
    const rawCharts = response.data.charts ?? [];
    const nextCharts = rawCharts.filter((chart) => Array.isArray(chart?.data) && chart.data.length > 0);
    setCharts(nextCharts);
    setStatus(nextCharts.length ? "Custom chart generated." : "No chart returned.");
  };

  const columnMeta: ColumnMeta[] = useMemo(
    () =>
      Array.isArray(datasetView?.columns)
        ? datasetView!.columns.map((c) => ({ name: String(c.name), dtype: String(c.dtype || "") }))
        : [],
    [datasetView],
  );
  const numericCols = useMemo(
    () => columnMeta.filter((c) => /^(int|float|double|decimal)/i.test(c.dtype)).map((c) => c.name),
    [columnMeta],
  );
  const allCols = useMemo(() => datasetView?.column_names ?? [], [datasetView]);

  const loadDashboards = async () => {
    const response = await api.get<{ dashboards: SavedDashboard[] }>("/datasets/dashboards");
    setDashboards(response.data.dashboards ?? []);
  };

  const saveCurrentDashboard = async () => {
    const name = dashboardName.trim() || `Dashboard ${dashboards.length + 1}`;
    const payload = {
      name,
      chart_type: chartType,
      x: chartX || null,
      y: chartY || null,
      color: chartColor || null,
      bins: chartBins,
      row_limit: chartRowLimit,
      filters: globalFilters,
    };
    const response = await api.post<{ dashboards: SavedDashboard[] }>("/datasets/dashboards", payload);
    setDashboards(response.data.dashboards ?? []);
    setDashboardName("");
    setStatus(`Saved dashboard "${name}".`);
  };

  const runDashboard = async (id: string) => {
    const response = await api.post<ChartResponse>(`/datasets/dashboards/${id}/run`);
    const nextCharts = (response.data.charts ?? []).filter((chart) => Array.isArray(chart?.data) && chart.data.length > 0);
    setCharts(nextCharts);
    setStatus(nextCharts.length ? "Dashboard chart loaded." : "Dashboard returned no chart data.");
  };

  const deleteDashboard = async (id: string) => {
    const response = await api.delete<{ dashboards: SavedDashboard[] }>(`/datasets/dashboards/${id}`);
    setDashboards(response.data.dashboards ?? []);
    setStatus("Dashboard deleted.");
  };

  const validateChartSelection = (): string | null => {
    if (chartType === "histogram" && !numericCols.includes(chartX)) return "Histogram requires numeric X column.";
    if (chartType === "scatter" || chartType === "heatmap") {
      if (!numericCols.includes(chartX) || !numericCols.includes(chartY)) {
        return `${chartType} requires numeric X and Y columns.`;
      }
    }
    if (chartType === "line" && !numericCols.includes(chartY)) return "Line chart requires numeric Y column.";
    if ((chartType === "bar" || chartType === "box") && chartY && !numericCols.includes(chartY)) {
      return `${chartType} chart requires numeric Y column.`;
    }
    return null;
  };

  const handleUpload = async () => {
    setIsBusy(true);
    setStatus("Uploading and profiling dataset...");
    try {
      if (file) {
        await uploadMultipart();
      } else if (filePath.trim()) {
        await uploadByPath();
      } else {
        setStatus("Choose a file or provide local path first.");
        return;
      }
      try {
        await fetchDataset();
      } catch {
        setStatus("Upload completed, but dataset preview failed to load.");
      }
    } catch (error: any) {
      setStatus(error?.response?.data?.detail ?? "Upload failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleChatSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const prompt = chatPrompt.trim();
    if (!prompt) return;

    setIsBusy(true);
    try {
      const response = await api.post<ChatResponse>("/datasets/chat", { message: prompt });
      setChatLog((prev) => [...prev, { question: prompt, answer: response.data }]);
      setChatPrompt("");
      setActiveTab("chat");
    } catch (error: any) {
      setStatus(error?.response?.data?.detail ?? "Chat request failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleTabClick = async (tabId: "dataset" | "profile" | "insights" | "charts" | "chat") => {
    setActiveTab(tabId);
    if (tabId === "chat") return;
    setIsBusy(true);
    try {
      if (tabId === "dataset") await fetchDataset();
      if (tabId === "profile") await fetchProfile();
      if (tabId === "insights") await fetchInsights();
      if (tabId === "charts") {
        if (!datasetView) await fetchDataset();
        await loadDashboards();
      }
    } catch (error: any) {
      setStatus(error?.response?.data?.detail ?? "Failed to load section.");
    } finally {
      setIsBusy(false);
    }
  };

  useEffect(() => {
    const bootstrapDataset = async () => {
      try {
        await fetchDataset();
      } catch {
        // Keep UI usable when no dataset exists yet.
      }
    };
    void bootstrapDataset();
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("analyticax-theme", theme);
  }, [theme]);

  const onGenerateChart = async () => {
    const validation = validateChartSelection();
    if (validation) {
      setStatus(validation);
      return;
    }
    setIsBusy(true);
    try {
      await fetchCustomChart();
      setActiveTab("charts");
    } catch (error: any) {
      setStatus(error?.response?.data?.detail ?? "Chart generation failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const onAddFilter = () => {
    const col = filterColumn.trim();
    const val = filterValue.trim();
    if (!col || !val) {
      setStatus("Choose filter column and value.");
      return;
    }
    setGlobalFilters((prev) => [...prev, { column: col, operator: filterOperator, value: val }]);
    setFilterValue("");
  };

  const onRemoveFilter = (idx: number) => {
    setGlobalFilters((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div className="app-shell">
      <PageHeader
        title="AnalyticaX"
        subtitle="AI-powered analytics studio for faster business decisions."
        status={status}
        logoSrc="/analyticax-logo.png"
        theme={theme}
        onThemeChange={setTheme}
      />

      <section className="hero-grid">
        {heroStats.map((item) => (
          <article key={item.label} className="hero-card">
            <p>{item.label}</p>
            <h3>{item.value}</h3>
          </article>
        ))}
      </section>

      <SectionCard className="upload-card">
        <div className="upload-grid">
          <label className="field">
            <span>Upload file (CSV/XLSX)</span>
            <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <label className="field">
            <span>Or use local file path</span>
            <input
              type="text"
              placeholder="D:\\data\\sales.csv"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
            />
          </label>
          <button className="primary-btn" disabled={isBusy} onClick={handleUpload}>
            {isBusy ? <Loader2 size={16} className="spin" /> : <Upload size={16} />}
            Upload Dataset
          </button>
        </div>
      </SectionCard>

      <SectionCard>
        <nav className="tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "tab active" : "tab"}
              onClick={() => handleTabClick(tab.id)}
            >
              <tab.icon size={15} className="tab-icon" />
              {tab.label}
            </button>
          ))}
        </nav>

        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18 }}
        >
          {activeTab === "dataset" && (
            <DatasetTab
              dataset={datasetView}
              onRetry={() => void handleTabClick("dataset")}
              formatCell={formatCell}
            />
          )}
          {activeTab === "profile" && <ProfileTab profile={profile} formatCell={formatCell} />}
          {activeTab === "insights" && (
            <InsightsTab
              insights={insights}
              charts={charts}
              chatLog={chatLog}
              onRegenerate={async () => {
                setIsBusy(true);
                try {
                  await fetchInsights();
                } catch (error: any) {
                  setStatus(error?.response?.data?.detail ?? "Insights regeneration failed.");
                } finally {
                  setIsBusy(false);
                }
              }}
              isBusy={isBusy}
            />
          )}
          {activeTab === "charts" && (
            <ChartsTab
              charts={charts}
              allCols={allCols}
              chartType={chartType}
              chartX={chartX}
              chartY={chartY}
              chartColor={chartColor}
              chartBins={chartBins}
              chartRowLimit={chartRowLimit}
              globalFilters={globalFilters}
              filterColumn={filterColumn}
              filterOperator={filterOperator}
              filterValue={filterValue}
              dashboardName={dashboardName}
              dashboards={dashboards}
              isBusy={isBusy}
              setChartType={setChartType}
              setChartX={setChartX}
              setChartY={setChartY}
              setChartColor={setChartColor}
              setChartBins={setChartBins}
              setChartRowLimit={setChartRowLimit}
              setFilterColumn={setFilterColumn}
              setFilterOperator={setFilterOperator}
              setFilterValue={setFilterValue}
              setDashboardName={setDashboardName}
              onAddFilter={onAddFilter}
              onRemoveFilter={onRemoveFilter}
              onGenerate={onGenerateChart}
              onSaveDashboard={async () => {
                setIsBusy(true);
                try {
                  await saveCurrentDashboard();
                } catch (error: any) {
                  setStatus(error?.response?.data?.detail ?? "Failed to save dashboard.");
                } finally {
                  setIsBusy(false);
                }
              }}
              onRunDashboard={async (id) => {
                setIsBusy(true);
                try {
                  await runDashboard(id);
                } catch (error: any) {
                  setStatus(error?.response?.data?.detail ?? "Failed to run dashboard.");
                } finally {
                  setIsBusy(false);
                }
              }}
              onDeleteDashboard={async (id) => {
                setIsBusy(true);
                try {
                  await deleteDashboard(id);
                } catch (error: any) {
                  setStatus(error?.response?.data?.detail ?? "Failed to delete dashboard.");
                } finally {
                  setIsBusy(false);
                }
              }}
            />
          )}
          {activeTab === "chat" && (
            <ChatTab
              chatPrompt={chatPrompt}
              setChatPrompt={setChatPrompt}
              chatLog={chatLog}
              isBusy={isBusy}
              onSubmit={handleChatSubmit}
            />
          )}
        </motion.div>
      </SectionCard>
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString() : "-";
  return String(value);
}


export default App;
