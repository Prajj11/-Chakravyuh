"use client";
import { useState } from "react";
import { artifact, review } from "@/lib/api";
import { privateText, score } from "@/lib/privacy";
import type {
  ClaimVerificationStatus,
  NarrativeCampaignDetail,
} from "@/types/chakravyuh";
type Props = {
  detail: NarrativeCampaignDetail;
  token: string;
  privacy: boolean;
  onRefresh: () => Promise<void>;
};
export function ClaimPanel({ detail, token, privacy, onRefresh }: Props) {
  const [status, setStatus] =
      useState<ClaimVerificationStatus>("CONTEXT_MISSING"),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [snapshot, setSnapshot] = useState("");
  const claim = detail.claim_verification,
    reference = claim.candidate_reference;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!reference) return;
    setBusy(true);
    try {
      await review(
        detail.campaign_id,
        { reference_id: reference.reference_id, status, analyst_note: note },
        token,
      );
      setMessage(
        "Contextual review saved with authenticated reviewer and audit entry.",
      );
      await onRefresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Review failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">SIMILARITY IS NOT VERIFICATION</span>
          <h2>Claim context & review</h2>
        </div>
        <span className="chip">{claim.status}</span>
      </div>
      <blockquote>
        {privateText(detail.primary_narrative_claim, detail, privacy)}
      </blockquote>
      {reference ? (
        <>
          <div
            className={
              reference.synthetic_reference ? "notice synthetic" : "notice"
            }
          >
            {reference.synthetic_reference
              ? "SYNTHETIC DEMO ADVISORY — fictional exercise only. It cannot verify public or injected claims."
              : "Retained candidate reference — human context review required."}
          </div>
          <div className="comparison-text">
            <div>
              <h3>Observed wording</h3>
              <p>
                {privateText(detail.primary_narrative_claim, detail, privacy)}
              </p>
            </div>
            <div>
              <h3>{reference.source_title}</h3>
              <p>{privateText(reference.claim_text, detail, privacy)}</p>
              <small>
                Candidate similarity {score(claim.similarity_to_known_claim, 3)}{" "}
                · {reference.applicable_region ?? "No region specified"}
              </small>
            </div>
          </div>
          <dl className="facts">
            <dt>Published / retrieved UTC</dt>
            <dd>
              {reference.published_at_utc} / {reference.retrieved_at_utc}
            </dd>
            <dt>Snapshot SHA-256</dt>
            <dd className="hash">{reference.snapshot_sha256}</dd>
          </dl>
          <button
            onClick={async () => {
              try {
                setSnapshot(
                  await (await artifact(reference.snapshot_ref, token)).text(),
                );
              } catch (e) {
                setMessage(
                  e instanceof Error ? e.message : "Snapshot unavailable",
                );
              }
            }}
          >
            Read retained source snapshot
          </button>
          {snapshot && (
            <pre className="source-snapshot">
              {privateText(snapshot, detail, privacy)}
            </pre>
          )}
          <form onSubmit={submit} className="review-form">
            <h3>Record contextual analyst review</h3>
            <p className="subtle">
              Confirm the source addresses the same date, location, actors and
              media. The server assigns reviewer identity.
            </p>
            <label>
              Finding
              <select
                value={status}
                onChange={(e) =>
                  setStatus(e.target.value as ClaimVerificationStatus)
                }
              >
                <option value="CONTEXT_MISSING">Context missing</option>
                <option value="CONTRADICTED_BY_SOURCE">
                  Contradicted by source
                </option>
                <option value="CORROBORATED">Corroborated</option>
                <option value="UNVERIFIED">Unverified</option>
              </select>
            </label>
            <label>
              Contextual note
              <textarea
                required
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Explain the context checked and any unresolved limitations…"
              />
            </label>
            <button className="primary-button" disabled={busy || !note.trim()}>
              {busy ? "Saving review…" : "Save authenticated review"}
            </button>
          </form>
        </>
      ) : (
        <div className="empty">
          No context-valid retained reference meets the retrieval threshold.
          This claim remains unverified. Synthetic advisories are isolated from
          public/injected data.
        </div>
      )}
      {claim.reviewed_by && (
        <p className="notice">
          Reviewed by {claim.reviewed_by} at {claim.reviewed_at_utc}.{" "}
          {privateText(claim.analyst_note, detail, privacy)}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <ul className="reasons">
        {claim.evidence_reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}
