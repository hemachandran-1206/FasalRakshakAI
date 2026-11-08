import { CREDITS, TEAM, TEAM_TITLE } from "../credits.js";
import { useLang } from "../i18n.jsx";
import Icon from "./Icon.jsx";

export default function AboutPage() {
  const { t } = useLang();
  return (
    <section>
      <div className="pagehead"><span className="eyebrow">{t("hero_eyebrow")}</span><h1>{t("about_title")}</h1><p>{t("about_intro")}</p></div>

      <div className="card notice"><Icon name="alert" size={18} /> {t("about_warn")}</div>
      <div className="card white"><h2><Icon name="shield" size={18} /> {t("about_privacy").split(":")[0]}</h2><p className="muted">{t("about_privacy")}</p></div>

      <div className="card white">
        <h2><Icon name="users" size={18} /> {TEAM_TITLE}</h2>
        <div className="tablewrap">
          <table className="team">
            <thead><tr><th>{t("th_name")}</th><th>{t("th_entry")}</th></tr></thead>
            <tbody>{TEAM.map((m) => <tr key={m.entry}><td>{m.name}</td><td className="mono">{m.entry}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="muted" style={{ marginTop: 14 }}>{t("about_ai_built")}</p>
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
