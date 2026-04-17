import { useMemo, useRef, useState } from "react";
import type { ChartModel, ChatEntry, InsightItem, Insights } from "../../types/app";
import { FilterChip } from "../ui/FilterChip";
import { RechartsPlot } from "./ChartsTab";

type InsightsTabProps = {
  insights: Insights | null;
  charts: ChartModel[];
  chatLog: ChatEntry[];
  onRegenerate: () => void;
  isBusy: boolean;
};

export function InsightsTab({ insights, charts, chatLog, onRegenerate, isBusy }: InsightsTabProps) {
  const [severityFilter, setSeverityFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [sortBy, setSortBy] = useState<"confidence" | "impact">("confidence");
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [reportTitle, setReportTitle] = useState("Data Insights Report");
  const [reportAuthor, setReportAuthor] = useState("");
  const [reportNotes, setReportNotes] = useState("");
  const [includeCharts, setIncludeCharts] = useState(true);
  const [includePinnedOnly, setIncludePinnedOnly] = useState(false);
  const [featureInput, setFeatureInput] = useState("");
  const [customFeatures, setCustomFeatures] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const chartCaptureRef = useRef<HTMLDivElement | null>(null);

  const merged: Array<InsightItem & { id: string }> = useMemo(() => {
    if (!insights) return [];
    return [...(insights.insights ?? []), ...(insights.data_quality_risks ?? []), ...(insights.recommendations ?? [])].map(
      (item, idx) => ({
        ...item,
        id: `${item.category}-${idx}-${item.message.slice(0, 24)}`,
      }),
    );
  }, [insights]);

  const impactScore = (item: InsightItem) => {
    const sev = item.severity === "high" ? 3 : item.severity === "medium" ? 2 : 1;
    return sev * (Math.max(0, Math.min(100, item.confidence || 0)) / 100);
  };

  const sorted = [...merged].sort((a, b) => {
    if (sortBy === "confidence") return (b.confidence || 0) - (a.confidence || 0);
    return impactScore(b) - impactScore(a);
  });
  const filtered = sorted.filter((item) => severityFilter === "all" || item.severity === severityFilter);
  const finalItems = includePinnedOnly ? filtered.filter((i) => pinnedIds.includes(i.id)) : filtered;
  const grouped = {
    insight: finalItems.filter((x) => x.category === "insight"),
    risk: finalItems.filter((x) => x.category === "risk"),
    recommendation: finalItems.filter((x) => x.category === "recommendation"),
  };

  const togglePin = (id: string) => {
    setPinnedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const addFeature = () => {
    const text = featureInput.trim();
    if (!text) return;
    setCustomFeatures((prev) => [...prev, text]);
    setFeatureInput("");
  };

  const removeFeature = (idx: number) => {
    setCustomFeatures((prev) => prev.filter((_, i) => i !== idx));
  };

  const exportPdf = async () => {
    setIsExporting(true);
    try {
      const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
        import("jspdf"),
        import("html2canvas"),
      ]);
      const pdf = new jsPDF({ orientation: "p", unit: "pt", format: "a4" });
      let y = 40;
      const pageW = pdf.internal.pageSize.getWidth();
      const write = (text: string, size = 11, bold = false) => {
        pdf.setFont("helvetica", bold ? "bold" : "normal");
        pdf.setFontSize(size);
        const lines = pdf.splitTextToSize(text, pageW - 80);
        lines.forEach((line: string) => {
          if (y > 790) {
            pdf.addPage();
            y = 40;
          }
          pdf.text(line, 40, y);
          y += size + 4;
        });
      };

      write(reportTitle, 18, true);
      write(`Author: ${reportAuthor || "N/A"} | Generated: ${new Date().toLocaleString()}`, 10);
      y += 6;
      write("Selected Features / Report Sections", 12, true);
      if (!customFeatures.length) write("- No custom features added.", 10);
      customFeatures.forEach((f) => write(`- ${f}`, 10));

      y += 8;
      write("Insights", 12, true);
      const exportItems = includePinnedOnly ? finalItems : filtered;
      if (!exportItems.length) write("- No insights matched selected filters.", 10);
      exportItems.forEach((item) => {
        write(`[${item.category.toUpperCase()} | ${item.severity.toUpperCase()} | ${item.confidence}%] ${item.message}`, 10, true);
        write(`Why: ${item.why}`, 10);
        write(`Action: ${item.action}`, 10);
        y += 4;
      });

      if (reportNotes.trim()) {
        y += 8;
        write("Additional Notes", 12, true);
        write(reportNotes.trim(), 10);
      }

      if (includeCharts) {
        y += 8;
        write("Charts Snapshot", 12, true);
        if (!charts.length) {
          write("- No generated charts available.", 10);
        } else {
          if (chartCaptureRef.current) {
            const nodes = Array.from(chartCaptureRef.current.querySelectorAll(".pdf-chart-image"));
            for (const node of nodes) {
              const canvas = await html2canvas(node as HTMLElement, { scale: 1.5, backgroundColor: "#ffffff" });
              const img = canvas.toDataURL("image/png");
              const w = pageW - 80;
              const h = Math.min((canvas.height * w) / canvas.width, 260);
              if (y + h > 790) {
                pdf.addPage();
                y = 40;
              }
              pdf.addImage(img, "PNG", 40, y, w, h);
              y += h + 12;
            }
          }
        }
      }

      y += 8;
      write("Chat Highlights", 12, true);
      if (!chatLog.length) {
        write("- No chat entries available.", 10);
      } else {
        chatLog.slice(-15).forEach((entry) => {
          write(`Q: ${entry.question}`, 10, true);
          write(`A: ${entry.answer.reply}`, 10);
        });
      }

      pdf.save(`${reportTitle.replace(/\s+/g, "_").toLowerCase() || "insights_report"}.pdf`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="insights-layout">
      <div className="insight-filters">
        {(["all", "high", "medium", "low"] as const).map((key) => (
          <FilterChip key={key} active={severityFilter === key} onClick={() => setSeverityFilter(key)}>
            {key.toUpperCase()}
          </FilterChip>
        ))}
        <FilterChip active={sortBy === "confidence"} onClick={() => setSortBy("confidence")}>
          SORT: CONFIDENCE
        </FilterChip>
        <FilterChip active={sortBy === "impact"} onClick={() => setSortBy("impact")}>
          SORT: IMPACT
        </FilterChip>
        <FilterChip active={includePinnedOnly} onClick={() => setIncludePinnedOnly((v) => !v)}>
          PINNED ONLY ({pinnedIds.length})
        </FilterChip>
        <button className="primary-btn" onClick={onRegenerate} disabled={isBusy}>
          {isBusy ? "Regenerating..." : "Regenerate with AI"}
        </button>
      </div>

      <div className="insights-grid">
        <InsightList title="Insights" items={grouped.insight} pinnedIds={pinnedIds} onTogglePin={togglePin} />
        <InsightList title="Data Quality Risks" items={grouped.risk} pinnedIds={pinnedIds} onTogglePin={togglePin} />
        <InsightList
          title="Recommendations"
          items={grouped.recommendation}
          pinnedIds={pinnedIds}
          onTogglePin={togglePin}
        />
      </div>

      <div className="report-builder card">
        <h3>Report Builder (PDF)</h3>
        <div className="report-grid">
          <label className="field">
            <span>Report title</span>
            <input value={reportTitle} onChange={(e) => setReportTitle(e.target.value)} />
          </label>
          <label className="field">
            <span>Author</span>
            <input value={reportAuthor} onChange={(e) => setReportAuthor(e.target.value)} />
          </label>
          <label className="field">
            <span>Custom feature/section</span>
            <div className="feature-row">
              <input value={featureInput} onChange={(e) => setFeatureInput(e.target.value)} placeholder="e.g., Include churn analysis section" />
              <button onClick={addFeature}>Add</button>
            </div>
          </label>
          <label className="field">
            <span>Notes</span>
            <textarea value={reportNotes} onChange={(e) => setReportNotes(e.target.value)} rows={3} />
          </label>
        </div>
        <div className="feature-list">
          {customFeatures.map((f, idx) => (
            <span key={`${f}-${idx}`} className="feature-tag">
              {f} <button onClick={() => removeFeature(idx)}>x</button>
            </span>
          ))}
        </div>
        <div className="report-options">
          <label><input type="checkbox" checked={includeCharts} onChange={(e) => setIncludeCharts(e.target.checked)} /> Include generated charts</label>
          <label><input type="checkbox" checked={includePinnedOnly} onChange={(e) => setIncludePinnedOnly(e.target.checked)} /> Export pinned insights only</label>
        </div>
        <button className="primary-btn" onClick={exportPdf} disabled={isExporting}>
          {isExporting ? "Exporting..." : "Export Insights to PDF"}
        </button>
      </div>

      <div className="pdf-capture-area" ref={chartCaptureRef}>
        {charts.map((chart, idx) => (
          <div className="pdf-chart-image" key={`pdf-chart-${idx}`}>
            <h4>{chart.title}</h4>
            <RechartsPlot chart={chart} />
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightList({
  title,
  items,
  pinnedIds,
  onTogglePin,
}: {
  title: string;
  items: Array<InsightItem & { id: string }>;
  pinnedIds: string[];
  onTogglePin: (id: string) => void;
}) {
  return (
    <article className="insight-card">
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={`${title}-${item.id}`}>
              <div className="insight-head">
                <span className={`severity-badge ${item.severity}`}>{item.severity}</span>
                <span className="confidence">Confidence: {Math.max(0, Math.min(100, item.confidence))}%</span>
              </div>
              <p className="insight-message">{item.message}</p>
              <details className="ai-details">
                <summary>AI details</summary>
                <p className="insight-meta">
                  <strong>Why:</strong> {item.why}
                </p>
                <p className="insight-meta">
                  <strong>Action:</strong> {item.action}
                </p>
                <p className="insight-meta">
                  <strong>Confidence:</strong> {Math.max(0, Math.min(100, item.confidence))}%
                </p>
              </details>
              <button className="pin-btn" onClick={() => onTogglePin(item.id)}>
                {pinnedIds.includes(item.id) ? "Unpin Insight" : "Pin Insight"}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p>No items yet.</p>
      )}
    </article>
  );
}
