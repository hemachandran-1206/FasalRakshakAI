import { CREDITS, TEAM } from "../credits.js";
import { useLang } from "../i18n.jsx";
import Icon from "./Icon.jsx";

export default function AboutPage() {
  const { t } = useLang();
  return (
    <section>
      <div className="pagehead"><span className="eyebrow">{t("hero_eyebrow")}</span><h1>{t("about_title")}</h1><p>{t("about_intro")}</p></div>

      <div className="card notice"><Icon name="alert" size={18} /> {t("about_warn")}</div>
      <div className="two">
        <div className="card white"><h2><Icon name="shield" size={18} /> {t("about_privacy").split(":")[0]}</h2><p className="muted">{t("about_privacy")}</p></div>
        <div className="card white">
          <h2><Icon name="users" size={18} /> {t("about_team")}</h2>
          <ul className="credit-list">{TEAM.map((m) => (
            <li key={m.name}><strong>{m.url ? <a href={m.url} target="_blank" rel="noreferrer noopener">{m.name}</a> : m.name}</strong><span className="muted">{m.role}</span></li>
          ))}</ul>
          <p className="muted">{t("about_ai_built")}</p>
        </div>
      </div>

      <h2 style={{ marginTop: 28 }}>{t("about_credits")}</h2>
      <p className="muted">{t("about_credits_intro")}</p>
      {CREDITS.map((g) => (
        <div className="card white" key={g.group}>
          <h3 style={{ marginTop: 0 }}>{g.group}</h3>
          <ul className="credit-list">
            {g.items.map((c) => (
              <li key={c.name}>
                <strong>{c.url ? <a href={c.url} target="_blank" rel="noreferrer noopener">{c.name}</a> : c.name}</strong>
                <span className="muted">{c.by}</span>
                <span className="badge">{t("about_licence")}: {c.license}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
