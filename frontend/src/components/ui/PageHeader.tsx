type PageHeaderProps = {
  title: string;
  subtitle: string;
  status: string;
  logoSrc?: string;
  theme: "midnight" | "graphite";
  onThemeChange: (theme: "midnight" | "graphite") => void;
};

export function PageHeader({ title, subtitle, status, logoSrc, theme, onThemeChange }: PageHeaderProps) {
  return (
    <header className="topbar glass">
      <div className="brand-block">
        {logoSrc ? <img src={logoSrc} alt={`${title} logo`} className="brand-logo" /> : null}
        {!logoSrc ? <h1>{title}</h1> : null}
        <p>{subtitle}</p>
      </div>
      <div className="header-actions">
        <label className="theme-switch">
          <span>Theme</span>
          <select value={theme} onChange={(e) => onThemeChange(e.target.value as "midnight" | "graphite")}>
            <option value="midnight">Midnight Blue</option>
            <option value="graphite">Graphite Gold</option>
          </select>
        </label>
        <div className="pill">{status}</div>
      </div>
    </header>
  );
}
