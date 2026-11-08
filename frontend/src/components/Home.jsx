import { useEffect, useState } from "react";
import { getReports } from "../api.js";
import { useLang } from "../i18n.jsx";
import Icon from "./Icon.jsx";

const CAPS = [["leaf", "cap_disease"], ["bug", "cap_pest"], ["cloud", "cap_weather"], ["pin", "cap_hot"], ["shield", "cap_expert"]];

export default function Home({ go }) {
  const { t } = useLang();
  const [count, setCount] = useState(null);
  // drop a real photo at public/images/hero.jpg to replace the illustrated fallback
  const [img, setImg] = useState("/images/hero.jpg");
  useEffect(() => { getReports().then((r) => setCount(r.length)).catch(() => {}); }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-img">
          <img src={img} alt="" onError={() => img !== "/images/hero-field.svg" && setImg("/images/hero-field.svg")} />
          {count != null && (
            <div className="float"><b>{count}</b><span>{t("stat_reports")}</span></div>
          )}
        </div>
        <div className="hero-copy">
          <span className="eyebrow">{t("hero_eyebrow")}</span>
          <h1>{t("hero_a")}<em>{t("hero_b")}</em></h1>
          <p className="lead">{t("hero_sub")}</p>
          <div className="cta-row">
            <button className="btn-primary btn-lg" onClick={() => go("detect")}>{t("cta_check")}<span className="go"><Icon name="arrow" size={18} /></span></button>
            <button className="btn-ghost" onClick={() => go("map")}>{t("cta_map")}</button>
          </div>
        </div>
      </section>
      <section className="caps">
        {CAPS.map(([ic, k]) => (
          <div className="cap hoverable" key={k}>
            <div className="ic"><Icon name={ic} /></div>
            <h3>{t(k)}</h3><p>{t(k + "_d")}</p>
          </div>
        ))}
      </section>
    </>
  );
}
