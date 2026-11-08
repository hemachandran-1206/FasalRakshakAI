import { useEffect, useMemo, useState } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { getHotspots, getReports } from "../api.js";
import { useLang } from "../i18n.jsx";

const ROPAR = [30.97, 76.52];
// colour-blind-aware categorical set; the confirmed/potential distinction is also carried by solid vs dashed rings
const COLORS = ["#C8452F", "#2A6FB0", "#557B35", "#7E57C2", "#E08A00", "#8C564B"];

export default function MapPage() {
  const { t } = useLang();
  const [reports, setReports] = useState([]);
  const [hot, setHot] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    Promise.all([getReports(), getHotspots()])
      .then(([r, h]) => { setReports(r); setHot(h); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const diseases = useMemo(() => [...new Set(reports.map((r) => r.disease))], [reports]);
  const colorOf = (d) => COLORS[Math.max(0, diseases.indexOf(d)) % COLORS.length];
  const shownReports = reports.filter((r) => !filter || r.disease === filter);
  const shownHot = (hot?.hotspots ?? []).filter((h) => !filter || h.disease === filter);
  const confirmed = shownHot.filter((h) => h.confirmed).length;

  return (
    <section>
      <div className="pagehead"><span className="eyebrow">{t("cap_hot")}</span><h1>{t("tab_map")}</h1>
        {hot && <p>≥ {hot.parameters.min_reports} · {hot.parameters.radius_km} km · {hot.parameters.window_days} d. {t("map_note")}</p>}</div>
      {error && <div className="card error" role="alert">{error}</div>}

      <div className="stats">
        <div className="stat"><small>{t("map_reports")}</small><b>{loading ? "–" : shownReports.length}</b></div>
        <div className="stat"><small>{t("map_hotspots")}</small><b>{loading ? "–" : shownHot.length - confirmed}</b></div>
        <div className="stat"><small>{t("map_confirmed")}</small><b>{loading ? "–" : confirmed}</b></div>
      </div>

      {diseases.length > 0 && (
        <div className="chips" role="group" aria-label="Disease filter">
          <button className={`chip ${!filter ? "on" : ""}`} onClick={() => setFilter("")}>{t("map_all")}</button>
          {diseases.map((d) => <button key={d} className={`chip ${filter === d ? "on" : ""}`} onClick={() => setFilter(d)}>
            <span className="dot" style={{ background: colorOf(d), marginRight: 6 }} />{d}</button>)}
        </div>
      )}

      {loading ? <div className="skeleton" style={{ height: 420 }} /> : (
        <div className="mapbox">
          <MapContainer center={ROPAR} zoom={10} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                       url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {shownReports.map((r, i) => (
              <CircleMarker key={i} center={[r.latitude, r.longitude]} radius={7}
                            pathOptions={{ color: "#fff", weight: 2, fillColor: colorOf(r.disease), fillOpacity: 0.9 }}>
                <Popup>{r.crop} — {r.disease}<br />{new Date(r.created_at).toLocaleString()}<br />{r.verified ? "Expert-verified" : "Unverified AI suggestion"}</Popup>
              </CircleMarker>
            ))}
            {shownHot.map((h, i) => (
              <Circle key={i} center={[h.latitude, h.longitude]} radius={h.radius_km * 1000}
                      pathOptions={{ color: colorOf(h.disease), weight: h.confirmed ? 3 : 2, dashArray: h.confirmed ? undefined : "6", fillOpacity: h.confirmed ? 0.18 : 0.08 }}>
                <Popup><strong>{h.confirmed ? t("lg_confirmed") : t("lg_potential")}</strong><br />
                  {h.disease} ({h.crops.join(", ")})<br />{h.report_count} reports · {h.verified_count} expert-verified</Popup>
              </Circle>
            ))}
          </MapContainer>
        </div>
      )}

      <div className="legend" aria-label={t("legend")}>
        <strong>{t("legend")}:</strong>
        <span><i className="dot" style={{ background: "#557B35" }} />{t("lg_report")}</span>
        <span><i className="ring dash" />{t("lg_potential")}</span>
        <span><i className="ring" style={{ borderWidth: 3 }} />{t("lg_confirmed")}</span>
      </div>

      <div className="card">
        <h2>{t("map_hotspots")}</h2>
        {hot && shownHot.length === 0 && <p className="muted">{t("map_empty")} {reports.length} {t("map_reports").toLowerCase()}.</p>}
        {shownHot.map((h, i) => (
          <div className="cand" key={i}>
            <span><i className="dot" style={{ background: colorOf(h.disease), marginRight: 8 }} /><strong>{h.disease}</strong> · {h.crops.join(", ")}</span>
            <span>{h.report_count} ({h.verified_count} ✓) <span className={`badge ${h.confirmed ? "ok" : "moderate"}`}>{h.confirmed ? t("map_confirmed") : t("map_hotspots")}</span></span>
          </div>
        ))}
      </div>
    </section>
  );
}
