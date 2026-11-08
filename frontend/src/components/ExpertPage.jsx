import { useCallback, useEffect, useState } from "react";
import { expertReview, expertReviews, getCatalogue, submitDecision } from "../api.js";
import ReviewPanel from "./ReviewPanel.jsx";

function DecisionForm({ review, onDone, catalogue }) {
  const [decision, setDecision] = useState("confirm");
  const [crop, setCrop] = useState(review.ai_crop);
  const [disease, setDisease] = useState("");
  const [notes, setNotes] = useState("");
  const [advMgmt, setAdvMgmt] = useState("");
  const [advPrev, setAdvPrev] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  if (review.status !== "assigned") return null;
  const known = catalogue.find((c) => c.name.toLowerCase() === crop.trim().toLowerCase() || c.id === crop.trim().toLowerCase());

  async function submit(e) {
    e.preventDefault(); setError(null); setBusy(true);
    try {
      const body = { decision, notes };
      if (decision === "correct") Object.assign(body, { crop, disease });
      if (decision !== "inconclusive" && (advMgmt.trim() || advPrev.trim())) Object.assign(body, { advice_management: advMgmt, advice_prevention: advPrev });
      onDone(await submitDecision(review.id, body));
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={submit} className="stack decision">
      <h3>Your decision</h3>
      <label className="check"><input type="radio" checked={decision === "confirm"} onChange={() => setDecision("confirm")} />
        Confirm the AI prediction ({review.ai_crop} — {review.ai_disease})</label>
      <label className="check"><input type="radio" checked={decision === "correct"} onChange={() => setDecision("correct")} />
        Correct it</label>
      {decision === "correct" && (
        <div className="inline">
          <label>Crop<input list="crop-list" value={crop} onChange={(e) => setCrop(e.target.value)} required /></label>
          <label>Disease / pest<input list="disease-list" value={disease} onChange={(e) => setDisease(e.target.value)} required /></label>
          <datalist id="crop-list">{catalogue.map((c) => <option key={c.id} value={c.name} />)}</datalist>
          <datalist id="disease-list">{(known?.diseases ?? []).map((d) => <option key={d} value={d} />)}</datalist>
        </div>
      )}
      <label className="check"><input type="radio" checked={decision === "inconclusive"} onChange={() => setDecision("inconclusive")} />
        Inconclusive (reason required)</label>
      <label>Notes for the farmer (shown on their case page)<textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} required={decision === "inconclusive"} /></label>
      {decision !== "inconclusive" && (
        <details><summary>Add treatment advice for this disease (optional)</summary>
          <p className="muted">Saved as an English draft for staff to review and translate. Never overwrites existing advice. Fill both boxes or neither.</p>
          <label>Treatment / management<textarea rows={3} value={advMgmt} onChange={(e) => setAdvMgmt(e.target.value)} /></label>
          <label>Prevention / cultural practice<textarea rows={3} value={advPrev} onChange={(e) => setAdvPrev(e.target.value)} /></label>
        </details>
      )}
      {error && <p className="errtext">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Saving…" : "Submit decision"}</button>
      <p className="muted">Decisions are final once submitted.</p>
    </form>
  );
}

export default function ExpertPage() {
  const [status, setStatus] = useState("assigned");
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [catalogue, setCatalogue] = useState([]);
  useEffect(() => { getCatalogue().then((c) => setCatalogue(c.crops)).catch(() => {}); }, []);

  const load = useCallback(async () => {
    try { setError(null); setRows(await expertReviews(status)); } catch (e) { setError(e.message); }
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const open = async (id) => { try { setSelected(await expertReview(id)); } catch (e) { setError(e.message); } };
  const done = (updated) => { setSelected(updated); load(); };

  return (
    <>
      <div className="card white">
        <h2>My cases</h2>
        <label>Show
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="assigned">To review</option><option value="all">All my cases</option>
          </select>
        </label>
        {error && <p className="errtext">{error}</p>}
        {rows.length === 0 ? <p className="muted">Nothing to review right now.</p> : (
          <div className="tablewrap"><table>
            <thead><tr><th>Submitted</th><th>AI prediction</th><th>Conf.</th><th>Status</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} onClick={() => open(r.id)} className={selected?.id === r.id ? "sel" : ""}>
                <td>{new Date(r.created_at).toLocaleDateString()}</td>
                <td>{r.ai_crop} — {r.ai_disease} {r.needs_attention && <span className="badge moderate">!</span>}</td>
                <td>{r.ai_confidence}%</td><td>{r.status}</td>
              </tr>))}</tbody>
          </table></div>
        )}
      </div>
      {selected && <ReviewPanel review={selected} onClose={() => setSelected(null)} actions={<DecisionForm key={selected.id + selected.status} review={selected} onDone={done} catalogue={catalogue} />} />}
    </>
  );
}
