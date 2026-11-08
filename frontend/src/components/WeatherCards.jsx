import { useLang } from "../i18n.jsx";
import Icon from "./Icon.jsx";

// Weather is its own section: it shows favourable conditions for disease, never a diagnosis.
export default function WeatherCards({ weather }) {
  const { t } = useLang();
  if (!weather) return null;
  const tiles = [
    ["wx_temp", weather.temperature_c != null ? `${weather.temperature_c} °C` : "–"],
    ["wx_hum", weather.humidity_pct != null ? `${weather.humidity_pct}%` : "–"],
    ["wx_rain", weather.rainfall_7d_mm != null ? `${weather.rainfall_7d_mm} mm` : "–"],
  ];
  return (
    <div className="card white">
      <h2><Icon name="cloud" size={20} /> {t("wx_title")}</h2>
      <div className="wx-grid">
        {tiles.map(([k, v]) => <div className="fact" key={k}><small>{t(k)}</small><b>{v}</b></div>)}
      </div>
      {weather.risks.map((r) => (
        <div key={r.rule_id} className={`risk ${r.risk_level}`}>
          <div className="risk-head">
            <strong>{r.disease}</strong> <span className="muted">({r.crops.join(", ")})</span>
            <span className={`badge ${r.risk_level}`}>{t(`risk_${r.risk_level}`)}</span>
          </div>
          <p>{r.explanation}</p>
          <a href={r.source_url} target="_blank" rel="noreferrer">Source: ICAR</a>
        </div>
      ))}
      <p className="muted">{t("wx_note")}</p>
    </div>
  );
}
