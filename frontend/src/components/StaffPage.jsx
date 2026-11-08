import AdvisoriesPage from "./AdvisoriesPage.jsx";
import Icon from "./Icon.jsx";
import { useState } from "react";
import { changePassword, login, tokenStore } from "../api.js";
import AdminPage from "./AdminPage.jsx";
import ExpertPage from "./ExpertPage.jsx";

function LoginForm({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const res = await login(email, password);
      tokenStore.set(res.access_token);
      onLogin(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="card narrow white">
      <h2>Staff login</h2>
      <p className="muted">For administrators and agricultural experts.</p>
      <label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      {error && <p className="errtext">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    </form>
  );
}

function PasswordForm() {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState(null);
  async function submit(e) {
    e.preventDefault();
    try { await changePassword(cur, next); setMsg("Password changed."); setCur(""); setNext(""); }
    catch (err) { setMsg(err.message); }
  }
  return (
    <details className="card white" open>
      <summary>Change password</summary>
      <form onSubmit={submit} className="stack">
        <label>Current password<input type="password" value={cur} onChange={(e) => setCur(e.target.value)} required /></label>
        <label>New password (min 10 characters)<input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={10} /></label>
        <button type="submit">Update</button>
        {msg && <p className="muted">{msg}</p>}
      </form>
    </details>
  );
}

export default function StaffPage({ user, onLogin, onLogout }) {
  const [section, setSection] = useState("queue");
  if (!user) return <LoginForm onLogin={onLogin} />;
  const admin = user.role === "admin";
  const items = admin
    ? [["queue", "list", "Reviews"], ["experts", "users", "Experts"], ["advisories", "book", "Advisories"], ["account", "user", "Account"]]
    : [["queue", "list", "My cases"], ["advisories", "book", "Advisories"], ["account", "user", "Account"]];
  return (
    <section className="staff">
      <aside className="side" aria-label="Staff navigation">
        <div className="who"><b>{user.full_name}</b><span className="muted">{user.role}</span></div>
        {items.map(([id, ic, label]) => (
          <button key={id} className={section === id ? "active" : ""} onClick={() => setSection(id)}><Icon name={ic} size={18} />{label}</button>
        ))}
        <button onClick={onLogout}>Sign out</button>
      </aside>
      <div>
        {section === "queue" && (admin ? <AdminPage section="queue" /> : <ExpertPage />)}
        {section === "experts" && admin && <AdminPage section="experts" />}
        {section === "advisories" && <AdvisoriesPage role={user.role} />}
        {section === "account" && <PasswordForm />}
      </div>
    </section>
  );
}
