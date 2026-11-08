import { useEffect, useState } from "react";
import { reviewImageUrl } from "../api.js";
import ImageWithBoxes from "./ImageWithBoxes.jsx";
import { getAdvisory } from "../api.js";

const when = (t) => (t ? new Date(t).toLocaleString() : "–");

// Shows one review: photo, AI prediction, history. `actions` is the role-specific part (assign / decide).
export default function ReviewPanel({ review, actions, onClose }) {
  const [img, setImg] = useState(null);
  const [imgError, setImgError] = useState(false);
  const [ref, setRef] = useState(null);
  useEffect(() => {
    setRef(null);
    if (review.ai_disease && !/not assessed/i.test(review.ai_disease) && !/healthy/i.test(review.ai_disease))
      getAdvisory(review.ai_crop, review.ai_disease).then(setRef).catch(() => {});
  }, [review.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let url;
    setImg(null); setImgError(false);
    reviewImageUrl(review.id).then((u) => { url = u; setImg(u); }).catch(() => setImgError(true));
    return () => url && URL.revokeObjectURL(url);
  }, [review.id]);

  return (
    <div className="card white">
      <div className="bar"><h2>Case {review.case_code ?? review.id.slice(0, 8)}</h2><button onClick={onClose}>Close</button></div>
      {img && <ImageWithBoxes src={img} boxes={review.pests} />}
      {imgError && <p className="muted">Image not available for this case.</p>}
      <p><strong>AI prediction:</strong> {review.ai_crop} — {review.ai_disease} ({review.ai_confidence}%)
        {review.needs_attention && <span className="badge moderate">needs attention</span>}</p>
      {review.top_k.length > 1 && (
        <p className="muted">Other candidates: {review.top_k.slice(1).map((c) => `${c.plant} — ${c.disease} ${c.confidence}%`).join("; ")}</p>
      )}
      {review.pests.length > 0 && <p className="muted">Pests: {review.pests.map((p) => `${p.pest} ${p.confidence}%`).join("; ")}</p>}
      <p className="muted">
        Status: <strong>{review.status}</strong> · Submitted {when(review.created_at)}
        {review.latitude != null && <> · Location {review.latitude}, {review.longitude}</>}
      </p>
      {review.expert_disease && (
        <p><strong>Expert answer:</strong> {review.expert_crop} — {review.expert_disease}{review.expert_notes && <> · <em>{review.expert_notes}</em></>}</p>
      )}
      {ref && (
        <details className="card"><summary>Reference advice for {review.ai_crop} — {review.ai_disease}</summary>
          <p><strong>Management:</strong> {ref.recommendation}</p><p><strong>Prevention:</strong> {ref.cultural_practice}</p>
          <p className="muted">Source: {ref.source || "—"}. Shown for the AI-predicted disease; your decision is separate.</p>
        </details>
      )}
      {actions}
      <h3>History</h3>
      <ul className="history">
        {review.history.map((h, i) => (
          <li key={i}><strong>{h.action}</strong> by {h.actor_name} · {when(h.created_at)}{h.note && <> — {h.note}</>}</li>
        ))}
      </ul>
    </div>
  );
}
