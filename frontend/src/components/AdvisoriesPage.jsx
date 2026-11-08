import { useCallback, useEffect, useState } from "react";
import { exportAdvisories, importAdvisories, listAdvisories, saveAdvisory, verifyAdvisory } from "../api.js";

const EMPTY = { crop: "", disease: "", language: "hi", symptoms: "", prevention: "", management: "", source: "", source_url: "" };

// Staff panel for Phase 4: edit translated advice, verify it, bulk import/export CSV (import/export: admin only).
export default function AdvisoriesPage({ role }) {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState({ language: "", status: "draft" });
  const [form, setForm] = useState(EMPTY);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const load = useCallback(async () => {
    try { setMsg(null); setRows(await listAdvisories(filter)); } catch (e) { setMsg(e.message); }
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  const wrap = (fn) => async (...a) => { try { setMsg(null); await fn(...a); await load(); } catch (e) { setMsg(e.message); } };
  const save = wrap(async (e) => { e.preventDefault(); await saveAdvisory(form); setMsg("Saved as draft. Verify it to show it to farmers."); });
  const verify = wrap((id) => verifyAdvisory(id));
  const upload = wrap(async (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (!f) return;
    const r = await importAdvisories(f);
    setMsg(`Imported ${r.imported_as_draft} as drafts, skipped ${r.skipped_blank} blank. ${r.errors.length ? "Errors: " + r.errors.join("; ") : ""}`);
  });
  async function download() {
    try {
      const url = await exportAdvisories();
      const a = document.createElement("a"); a.href = url; a.download = "advisories.csv"; a.click(); URL.revokeObjectURL(url);
    } catch (e) { setMsg(e.message); }
  }

  return (
    <div className="card white">
      <h2>Advisories (English / हिन्दी / ਪੰਜਾਬੀ)</h2>
      <p className="muted">Farmers only see <strong>verified</strong> text. Editing a verified row sends it back to draft.</p>
      <div className="inline">
        <label>Language<select value={filter.language} onChange={(e) => setFilter({ ...filter, language: e.target.value })}>
          <option value="">All</option><option value="en">English</option><option value="hi">हिन्दी</option><option value="pa">ਪੰਜਾਬੀ</option></select></label>
        <label>Crop<input value={filter.crop ?? ""} onChange={(e) => setFilter({ ...filter, crop: e.target.value })} placeholder="e.g. Potato" /></label>
        <label>Status<select value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })}>
          <option value="">All</option><option value="draft">Draft</option><option value="verified">Verified</option></select></label>
        {role === "admin" && <>
          <button type="button" onClick={download}>Download CSV template</button>
          <label className="file">Import CSV<input type="file" accept=".csv,text/csv" onChange={upload} /></label>
        </>}
      </div>
      {msg && <p className="muted">{msg}</p>}
      {rows.length === 0 ? <p className="muted">No advisories match.</p> : (
        <div className="tablewrap"><table>
          <thead><tr><th>Crop — disease</th><th>Lang</th><th>Status</th><th></th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id}>
              <td onClick={() => setForm({ ...EMPTY, ...r })} style={{ cursor: "pointer" }} title="Click to edit">{r.crop} — {r.disease}</td>
              <td>{r.language}</td>
              <td><span className={`badge ${r.verification_status === "verified" ? "ok" : "moderate"}`}>{r.verification_status}</span></td>
              <td>{r.verification_status === "draft" && <button type="button" onClick={() => verify(r.id)}>Verify</button>}</td>
            </tr>))}</tbody>
        </table></div>
      )}
      <details><summary>Add / edit an advisory</summary>
        <form onSubmit={save} className="stack">
          <div className="inline">
            <label>Crop<input value={form.crop} onChange={set("crop")} required /></label>
            <label>Disease<input value={form.disease} onChange={set("disease")} required /></label>
            <label>Language<select value={form.language} onChange={set("language")}>
              <option value="en">English</option><option value="hi">हिन्दी</option><option value="pa">ਪੰਜਾਬੀ</option></select></label>
          </div>
          <label>Treatment / management<textarea className="adv" rows={3} value={form.management} onChange={set("management")} /></label>
          <label>Prevention / cultural practice<textarea className="adv" rows={3} value={form.prevention} onChange={set("prevention")} /></label>
          <label>Symptoms (optional)<textarea className="adv" rows={2} value={form.symptoms} onChange={set("symptoms")} /></label>
          <div className="inline">
            <label>Source<input value={form.source} onChange={set("source")} placeholder="e.g. PAU Package of Practices" /></label>
            <label>Source URL<input value={form.source_url} onChange={set("source_url")} /></label>
          </div>
          <button type="submit">Save as draft</button>
        </form>
      </details>
    </div>
  );
}
