import { useEffect, useState } from "react";
import { getCase } from "../api.js";
import { recentCases } from "./caseStore.js";
import CareView, { Treatment } from "./CareView.jsx";
import WeatherCards from "./WeatherCards.jsx";
import Icon from "./Icon.jsx";
import { useLang } from "../i18n.jsx";

const STAGES = [["awaiting_review", "st_received"], ["under_review", "st_reviewing"], ["verified", "st_verified"]];

function Progress({ stage }) {
  const { t } = useLang();
  const idx = stage === "inconclusive" ? 2 : STAGES.findIndex(([s]) => s === stage);
  return (
    <ol className="steps">
      {STAGES.map(([s, label], i) => (
        <li key={s} className={i < idx ? "done" : i === idx ? "now" : ""}>
          {stage === "inconclusive" && s === "verified" ? t("st_inconclusive") : t(label)}
        </li>
      ))}
    </ol>
  );
}

export default function CasePage({ initialCode = "" }) {
  const { lang, t } = useLang();
  const [code, setCode] = useState(initialCode);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const recent = recentCases();

  async function lookup(c = code) {
    if (!c.trim()) return;
    setBusy(true); setError(null); setData(null);
    try { setData(await getCase(c.trim(), lang)); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  useEffect(() => { if (initialCode) lookup(initialCode); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // switching language re-fetches the same case so the text matches
  useEffect(() => { if (data) getCase(data.case_code, lang).then(setData).catch(() => {}); }, [lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const [copied, setCopied] = useState(false);
  const care = data?.ai.care;
  const verified = data?.stage === "verified";

  return (
    <section>
      <div className="pagehead"><span className="eyebrow">{t("hero_eyebrow")}</span><h1>{t("tab_case")}</h1><p>{t("case_help")}</p></div>
      <form className="card white" onSubmit={(e) => { e.preventDefault(); lookup(); }}>
        <label>{t("enter_code")}
          <input className="codeinput" value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. K7M2-QX9P"
                 autoCapitalize="characters" autoComplete="off" spellCheck={false} maxLength={14} />
        </label>
        <button type="submit" disabled={busy || !code.trim()}><Icon name="search" size={16} /> {busy ? t("checking") : t("tab_case")}</button>
        {recent.length > 0 && (
          <p className="muted">{t("recent")} {recent.map((c) => (
            <button type="button" key={c} className="linkbtn" onClick={() => { setCode(c); lookup(c); }}>{c}</button>))}
          </p>
        )}
      </form>

      {error && <div className="card error" role="alert">{error}</div>}
      {busy && <div className="skeleton" style={{ height: 160, margin: "16px 0" }} />}

      {data && (
        <>
          <div className="card white">
            <div className="casecode">
              <div className="muted">{t("case_word")}</div>
              <div className="code">{data.case_code}</div>
              <button type="button" className="btn-primary" onClick={() => { navigator.clipboard?.writeText(data.case_code); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
                <Icon name={copied ? "check" : "copy"} size={16} /> {copied ? t("copied") : t("copy_code")}</button>
            </div>
            <h3>{t("review_status")}</h3>
            <Progress stage={data.stage} />
            <p>{data.message}</p>
            <p className="muted">{t("submitted")} {new Date(data.submitted_at).toLocaleString()}</p>
          </div>

          {verified && data.expert && (
            <div className="card verified">
              <h2>{t("expert_dx")}</h2>
              <p><strong>{data.expert.crop} — {data.expert.disease}</strong>
                {" "}<span className="muted">({data.expert.agrees_with_ai ? t("agrees") : t("differs")})</span></p>
              {data.expert.notes && <p><strong>{t("expert_notes")}</strong> {data.expert.notes}</p>}
              {data.final_treatment && <Treatment t={data.final_treatment} heading={t("verified_tx")} />}
              {data.treatment_note && <p>{data.treatment_note}</p>}
            </div>
          )}

          {data.stage === "inconclusive" && data.expert?.notes && (
            <div className="card notice"><strong>{t("expert_notes")}</strong> {data.expert.notes}</div>
          )}

          <div className={`card white ${verified && !data.expert?.agrees_with_ai ? "dim" : ""}`}>
            <h2>{t("ai_result")} {verified ? `(${t("prelim")})` : ""}</h2>
            <CareView care={care} superseded={verified && !data.expert?.agrees_with_ai} />
            {data.ai.pests.length > 0 && <p><strong>{t("pests_seen")}</strong> {data.ai.pests.map((p) => `${p.pest} (${p.confidence}%)`).join(", ")}</p>}
          </div>

          <WeatherCards weather={data.weather} />
        </>
      )}
    </section>
  );
}
