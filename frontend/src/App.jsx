import { useEffect, useState } from "react";
import { me, setUnauthorizedHandler, tokenStore } from "./api.js";
import Home from "./components/Home.jsx";
import DetectPage from "./components/DetectPage.jsx";
import CasePage from "./components/CasePage.jsx";
import AboutPage from "./components/AboutPage.jsx";
import MapPage from "./components/MapPage.jsx";
import StaffPage from "./components/StaffPage.jsx";
import Icon from "./components/Icon.jsx";
import { LANGS, useLang } from "./i18n.jsx";

export default function App() {
  const { lang, setLang, t } = useLang();
  const [tab, setTab] = useState("home");
  const [menu, setMenu] = useState(false);
  const [user, setUser] = useState(null);
  const [trackCode, setTrackCode] = useState("");
  const [booting, setBooting] = useState(!!tokenStore.get());

  const logout = () => { tokenStore.clear(); setUser(null); };
  const go = (id) => { setTab(id); setMenu(false); window.scrollTo?.({ top: 0 }); };

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (tokenStore.get()) me().then(setUser).catch(logout).finally(() => setBooting(false));
  }, []);

  const items = [
    ["detect", t("tab_detect")], ["case", t("tab_case")], ["map", t("tab_map")], ["about", t("tab_about")],
    ["staff", user ? `${user.role === "admin" ? "Admin" : "Expert"} panel` : t("tab_staff")],
  ];

  return (
    <div className="app">
      <div className="shell">
        <header className="topbar">
          <button className="brand" onClick={() => go("home")} aria-label="FasalRakshak AI">
            <span className="mark"><Icon name="leaf" size={20} /></span>
            <span className="word">FasalRakshak<em>AI</em></span>
          </button>
          <nav className={`main ${menu ? "open" : ""}`} aria-label="Main">
            {items.map(([id, label]) => (
              <button key={id} className={tab === id ? "active" : ""} aria-current={tab === id ? "page" : undefined} onClick={() => go(id)}>{label}</button>
            ))}
          </nav>
          <div className="right">
            <select className="lang" aria-label={t("language")} value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
            </select>
            <button className="burger" aria-label={t("menu")} aria-expanded={menu} onClick={() => setMenu(!menu)}>
              <Icon name={menu ? "close" : "menu"} />
            </button>
          </div>
        </header>
        <main className="page" key={tab}>
          {tab === "home" && <Home go={go} />}
          {tab === "detect" && <DetectPage onTrack={(code) => { setTrackCode(code); go("case"); }} />}
          {tab === "case" && <CasePage initialCode={trackCode} />}
          {tab === "map" && <MapPage />}
          {tab === "about" && <AboutPage />}
          {tab === "staff" && (booting ? <div className="skeleton" style={{ height: 160 }} /> : <StaffPage user={user} onLogin={setUser} onLogout={logout} />)}
        </main>
        <footer>{t("footer")}<br /><button className="linkbtn" style={{ fontFamily: "inherit", textDecoration: "underline" }} onClick={() => go("about")}>{t("footer_credits")}</button></footer>
      </div>
    </div>
  );
}
