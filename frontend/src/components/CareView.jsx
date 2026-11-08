import { useLang } from "../i18n.jsx";
import Icon from "./Icon.jsx";

// Treatment advice text: management + prevention (+ symptoms when the API provides them).
export function Treatment({ t: tx, heading }) {
  const { t } = useLang();
  return (
    <div className="result-body">
      {heading && <h3>{heading}</h3>}
      {tx.translation_note && <p className="notice-line">ℹ️ {tx.translation_note}</p>}
      {tx.symptoms && <div className="sec"><h4>{t("sec_symptoms")}</h4><p>{tx.symptoms}</p></div>}
      <div className="sec"><h4>{t("sec_management")}</h4><p>{tx.recommendation}</p></div>
      <div className="sec"><h4>{t("sec_prevention")}</h4><p>{tx.cultural_practice}</p></div>
    </div>
  );
}

const TONE = { healthy: ["check", "tri_healthy"], diagnosed: ["leaf", "tri_diagnosed"], likely: ["alert", "tri_likely"], escalated: ["user", "tri_escalated"] };

// One AI answer in one of four triage states. Wording comes from the backend; this only lays it out.
export default function CareView({ care, superseded = false }) {
  const { t } = useLang();
  if (!care) return null;
  const [icon, label] = TONE[care.status] ?? TONE.escalated;
  const conf = care.confidence;
  return (
    <div className={`result tone-${care.status}`}>
      <div className="result-head">
        <span className="ic"><Icon name={icon} /></span>
        <div><h3>{t(label)}</h3><div className="sub">{t("prelim")}</div></div>
      </div>
      <div className="result-body">
        {care.status === "healthy" && <p className="ok">{care.message}</p>}

        {care.status === "diagnosed" && (
          <>
            <div className="facts">
              <div className="fact"><small>{t("crop_label")}</small><b>{care.plant}</b></div>
              <div className="fact"><small>{t("disease_label")}</small><b>{care.disease}</b></div>
              <div className="fact"><small>{t("conf_label")}</small><b>{conf}%</b>
                <div className="meter" role="progressbar" aria-valuenow={conf} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${Math.min(conf, 100)}%` }} /></div></div>
            </div>
            {superseded && <p className="muted">{t("superseded")}</p>}
          </>
        )}

        {care.status === "likely" && (
          <>
            <p><strong>{t("possible")}</strong></p>
            <p className="muted">{care.message}</p>
            {care.candidates?.map((c, i) => (
              <div className="cand" key={i}><span>{c.plant} — {c.disease}</span><strong>{c.confidence}%</strong></div>
            ))}
            {care.hint && <p className="notice-line">💡 {care.hint}</p>}
            <div className="sec"><h4>{t("sec_management")}</h4><p>{care.interim_advice}</p></div>
          </>
        )}

        {care.status === "escalated" && <p>{care.message}</p>}

        {(care.status === "likely" || care.status === "escalated") && (
          <div className="sec"><h4>{t("sec_review")}</h4><p>{t("review_pending")}</p></div>
        )}
      </div>
      {care.status === "diagnosed" && !superseded && <Treatment t={care} heading={t("ai_tx")} />}
    </div>
  );
}
