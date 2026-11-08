import { useCallback, useEffect, useState } from "react";
import { adminExperts, adminReview, adminReviews, assignReview, createExpert } from "../api.js";
import ReviewPanel from "./ReviewPanel.jsx";

export function ExpertsCard({ experts, reload }) {
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    try {
      await createExpert(form);
      setMsg("Expert account created. Share the password with them securely and ask them to change it.");
      setForm({ email: "", full_name: "", password: "" });
      reload();
    } catch (err) { setMsg(err.message); }
  }
  return (
    <div className="card white">
      <h2>Agricultural experts</h2>
      {experts.length === 0 ? <p className="muted">No experts yet — create one below.</p> : (
        <ul>{experts.map((x) => <li key={x.id}><strong>{x.full_name}</strong> ({x.email}) · {x.open_cases} open case(s)</li>)}</ul>
      )}
      <details><summary>Add an expert</summary>
        <form onSubmit={submit} className="stack">
          <label>Full name<input value={form.full_name} onChange={set("full_name")} required /></label>
          <label>Email<input type="email" value={form.email} onChange={set("email")} required /></label>
          <label>Temporary password (min 10 characters)<input type="text" value={form.password} onChange={set("password")} required minLength={10} /></label>
          <button type="submit">Create expert</button>
          {msg && <p className="muted">{msg}</p>}
        </form>
      </details>
    </div>
  );
}

function AssignBox({ review, experts, onDone }) {
  const [expertId, setExpertId] = useState("");
  const [error, setError] = useState(null);
  const final = ["confirmed", "corrected", "inconclusive"].includes(review.status);
  if (final) return <p className="muted">This review is completed.</p>;
  async function submit(e) {
    e.preventDefault(); setError(null);
    try { onDone(await assignReview(review.id, expertId)); } catch (err) { setError(err.message); }
  }
  return (
    <form onSubmit={submit} className="inline">
      <select value={expertId} onChange={(e) => setExpertId(e.target.value)} required>
        <option value="">Choose an expert…</option>
        {experts.map((x) => <option key={x.id} value={x.id}>{x.full_name} ({x.open_cases} open)</option>)}
      </select>
      <button type="submit">{review.assigned_expert ? "Reassign" : "Assign"}</button>
      {review.assigned_expert && <span className="muted">Currently: {review.assigned_expert.full_name}</span>}
      {error && <span className="errtext">{error}</span>}
    </form>
  );
}

export default function AdminPage({ section = "queue" }) {
  const [filters, setFilters] = useState({ status: "pending", needs_attention: "" });
  const [rows, setRows] = useState([]);
  const [experts, setExperts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [counts, setCounts] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [r, x] = await Promise.all([adminReviews(filters), adminExperts()]);
      setRows(r); setExperts(x);
      const all = await adminReviews({});
      const n = (s) => all.filter((a) => a.status === s).length;
      setCounts({ total: all.length, pending: n("pending"), assigned: n("assigned"), done: all.length - n("pending") - n("assigned"), attention: all.filter((a) => a.needs_attention && !["confirmed", "corrected", "inconclusive"].includes(a.status)).length });
    } catch (e) { setError(e.message); }
  }, [filters]);
  useEffect(() => { load(); }, [load]);

  const open = async (id) => { try { setSelected(await adminReview(id)); } catch (e) { setError(e.message); } };
  const assigned = (updated) => { setSelected(updated); load(); };

  return (
    <>
      {section === "experts" && <ExpertsCard experts={experts} reload={load} />}
      {section !== "experts" && <>
      {counts && (
        <div className="stats" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))" }}>
          <div className="stat"><small>Total reports</small><b>{counts.total}</b></div>
          <div className="stat"><small>Pending review</small><b>{counts.pending}</b></div>
          <div className="stat"><small>Assigned</small><b>{counts.assigned}</b></div>
          <div className="stat"><small>Completed</small><b>{counts.done}</b></div>
          <div className="stat"><small>Needs attention</small><b>{counts.attention}</b></div>
        </div>
      )}
      <div className="card white">
        <h2>Review queue</h2>
        <div className="inline">
          <label>Status
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              {["pending", "assigned", "confirmed", "corrected", "inconclusive"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label>Priority
            <select value={filters.needs_attention} onChange={(e) => setFilters({ ...filters, needs_attention: e.target.value })}>
              <option value="">All</option><option value="true">Needs attention</option><option value="false">Routine</option>
            </select>
          </label>
          <button onClick={load}>Refresh</button>
        </div>
        {error && <p className="errtext">{error}</p>}
        {rows.length === 0 ? <p className="muted">No reviews match.</p> : (
          <div className="tablewrap"><table>
            <thead><tr><th>Submitted</th><th>AI prediction</th><th>Conf.</th><th>Status</th><th>Expert</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} onClick={() => open(r.id)} className={selected?.id === r.id ? "sel" : ""}>
                <td>{new Date(r.created_at).toLocaleDateString()}</td>
                <td>{r.ai_crop} — {r.ai_disease} {r.needs_attention && <span className="badge moderate">!</span>}</td>
                <td>{r.ai_confidence}%</td><td>{r.status}</td><td>{r.assigned_expert?.full_name ?? "–"}</td>
              </tr>))}</tbody>
          </table></div>
        )}
      </div>
      {selected && (
        <ReviewPanel review={selected} onClose={() => setSelected(null)}
                     actions={<AssignBox review={selected} experts={experts} onDone={assigned} />} />
      )}
      </>}
    </>
  );
}
