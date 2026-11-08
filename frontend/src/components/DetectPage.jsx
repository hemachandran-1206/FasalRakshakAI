import { useEffect, useRef, useState } from "react";
import { detect, getCatalogue } from "../api.js";
import CareView from "./CareView.jsx";
import { getBrowserLocation } from "../geolocation.js";
import ImageWithBoxes from "./ImageWithBoxes.jsx";
import WeatherCards from "./WeatherCards.jsx";
import Icon from "./Icon.jsx";
import { rememberCase } from "./caseStore.js";
import { useLang } from "../i18n.jsx";

export default function DetectPage({ onTrack }) {
  const { lang, t } = useLang();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [over, setOver] = useState(false);
  const [shareLocation, setShareLocation] = useState(true);
  const [manual, setManual] = useState({ lat: "", lon: "" });
  const [showManual, setShowManual] = useState(false);
  const [crops, setCrops] = useState([]);
  const [crop, setCrop] = useState("");
  const [status, setStatus] = useState("idle");   // idle | locating | uploading | analysing
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [coordsUsed, setCoordsUsed] = useState(null);
  const [copied, setCopied] = useState(false);
  const fileInput = useRef(null);
  const camInput = useRef(null);

  useEffect(() => { getCatalogue().then((c) => setCrops(c.crops)).catch(() => {}); }, []);
  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const pick = (f) => { if (f) { setFile(f); setResult(null); setError(null); } };
  const onDrop = (e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files?.[0]); };

  function manualCoords() {
    const lat = parseFloat(manual.lat), lon = parseFloat(manual.lon);
    return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { latitude: lat, longitude: lon } : null;
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null); setResult(null); setProgress(0);
    let coords = manualCoords();
    if (!coords && shareLocation) {
      setStatus("locating");
      coords = await getBrowserLocation();
      if (!coords) setShowManual(true);
    }
    setCoordsUsed(coords);
    setStatus("uploading");
    try {
      const res = await detect(file, coords, crop, lang, (p) => { setProgress(p); if (p >= 1) setStatus("analysing"); });
      if (res.case_code) rememberCase(res.case_code);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  const busy = status !== "idle";
  const label = { locating: t("locating"), uploading: `${t("uploading")} ${Math.round(progress * 100)}%`, analysing: t("analysing") }[status] ?? t("diagnose");
  const copy = () => { navigator.clipboard?.writeText(result.case_code); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  return (
    <section>
      <div className="pagehead"><span className="eyebrow">{t("hero_eyebrow")}</span><h1>{t("tab_detect")}</h1></div>
      <div className="two">
        <form onSubmit={onSubmit} className="card detect white">
          {!file ? (
            <div className={`drop ${over ? "over" : ""}`} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
                 onDrop={onDrop} onClick={() => fileInput.current?.click()} role="button" tabIndex={0}
                 onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileInput.current?.click()}>
              <span className="ic"><Icon name="upload" size={26} /></span>
              <strong>{t("drop_title")}</strong>
              <span className="muted">{t("drop_hint")}</span>
              <div className="drop-actions" onClick={(e) => e.stopPropagation()}>
                <button type="button" className="btn-primary" onClick={() => camInput.current?.click()}><Icon name="camera" size={16} /> {t("take_photo")}</button>
                <button type="button" onClick={() => fileInput.current?.click()}>{t("choose_file")}</button>
              </div>
            </div>
          ) : (
            <div className="preview">
              <img src={preview} alt="" />
              <button type="button" className="change" onClick={() => setFile(null)}>{t("change_photo")}</button>
            </div>
          )}
          <input ref={fileInput} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => pick(e.target.files[0])} />
          <input ref={camInput} type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files[0])} />

          <div className="tip"><Icon name="alert" size={18} /><span>{t("quality_tip")}</span></div>

          <label>{t("which_crop")}
            <select value={crop} onChange={(e) => setCrop(e.target.value)}>
              <option value="">{t("not_sure")}</option>
              {crops.map((c) => <option key={c.id} value={c.id}>{c.name}{c.ai_supported ? "" : t("expert_review")}</option>)}
            </select>
          </label>
          <p className="muted">{t("crop_help")}</p>

          <label className="check">
            <input type="checkbox" checked={shareLocation} onChange={(e) => setShareLocation(e.target.checked)} />
            {t("use_location")}
          </label>
          <button type="button" className="linkbtn" style={{ fontFamily: "inherit" }} onClick={() => setShowManual(!showManual)}>{t("manual_loc")}</button>
          {showManual && (
            <>
              {shareLocation && status === "idle" && result && !coordsUsed && <p className="notice-line">{t("loc_failed")}</p>}
              <div className="coords">
                <label>{t("lat")}<input inputMode="decimal" placeholder="30.97" value={manual.lat} onChange={(e) => setManual({ ...manual, lat: e.target.value })} /></label>
                <label>{t("lon")}<input inputMode="decimal" placeholder="76.52" value={manual.lon} onChange={(e) => setManual({ ...manual, lon: e.target.value })} /></label>
              </div>
            </>
          )}

          {busy && <div className={`progress ${status === "uploading" ? "" : "indet"}`}><i style={status === "uploading" ? { width: `${progress * 100}%` } : undefined} /></div>}
          <div style={{ marginTop: 14 }}>
            <button type="submit" disabled={!file || busy}>{label}</button>
          </div>
        </form>

        <div>
          {error && <div className="card error" role="alert">{error}</div>}
          {busy && !result && <div className="skeleton" style={{ height: 220, margin: "16px 0" }} />}
          {!result && !busy && !error && (
            <div className="card lime"><Icon name="leaf" size={26} /><h2 style={{ marginTop: 10 }}>{t("hero_b")}</h2><p className="muted">{t("hero_sub")}</p></div>
          )}
          {result && (
            <>
              {shareLocation && !coordsUsed && <div className="card notice">{t("loc_skipped")}</div>}
              <div className="card white">
                <h2>{t("result_title")}</h2>
                {result.warnings?.map((w, i) => <p key={i} className="notice-line">📷 {w}</p>)}
                <CareView care={result.care} />
                <div className="casecode">
                  <div className="muted">{t("your_code")}</div>
                  <div className="code">{result.case_code}</div>
                  <div className="inline">
                    <button type="button" className="btn-primary" onClick={copy}><Icon name={copied ? "check" : "copy"} size={16} /> {copied ? t("copied") : t("copy_code")}</button>
                    <button type="button" onClick={() => onTrack(result.case_code)}>{t("check_later")}</button>
                  </div>
                  <p className="muted">{t("code_help")}</p>
                </div>
              </div>
              <div className="card white">
                <h2>{t("pests_title")}</h2>
                {preview && <ImageWithBoxes src={preview} boxes={result.pests} />}
                {result.pests.length === 0
                  ? <p className="muted">{t("no_pests")}</p>
                  : <ul>{result.pests.map((p, i) => <li key={i}><strong>{p.pest}</strong> — {p.confidence}%</li>)}</ul>}
              </div>
              <WeatherCards weather={result.weather} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
