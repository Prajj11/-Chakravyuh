"""Integrity-gated dossiers with uniform privacy transforms and manifest-linked bytes."""

import base64
import html
import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import stix2
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.evidence.canonical import JSONValue, canonical_bytes, sha256
from app.evidence.store import IntegrityMismatch
from app.pipeline import summary
from app.repositories.state import StateRepository
from app.schemas.models import (
    AccountRole,
    AuditTrailEntry,
    EvidenceArtifact,
    EvidenceDossierBundle,
    ExportRequest,
    NarrativeCampaignDetail,
    NarrativeCampaignSummary,
)


class PrivacyTransform:
    def __init__(self, detail: NarrativeCampaignDetail, enabled: bool) -> None:
        self.mapping = {}
        self.masked = {
            node.id
            for node in detail.nodes
            if enabled and node.role in {AccountRole.ORGANIC_USER, AccountRole.UNCLASSIFIED}
        }
        for event in detail.sample_posts:
            if event.account.account_id in self.masked:
                alias = "Participant_" + sha256(event.account.account_id.encode())[:12]
                for original in (
                    event.account.account_id,
                    event.account.handle,
                    event.account.handle.lstrip("@"),
                    event.account.display_name,
                ):
                    if original:
                        self.mapping[original] = alias

    def text(self, value: str) -> str:
        for original, replacement in sorted(self.mapping.items(), key=lambda pair: -len(pair[0])):
            value = re.sub(
                r"(?<!\w)" + re.escape(original) + r"(?!\w)",
                replacement,
                value,
                flags=re.IGNORECASE,
            )
        return value

    def apply(self, value: JSONValue) -> JSONValue:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.apply(item) for item in value]
        if isinstance(value, dict):
            return {self.text(key): self.apply(item) for key, item in value.items()}
        return value

    def detail(self, detail: NarrativeCampaignDetail) -> dict[str, JSONValue]:
        body = detail.model_dump(mode="json")
        for post in body["sample_posts"]:
            if post["account"]["account_id"] in self.masked:
                for key in (
                    "display_name",
                    "created_at",
                    "followers_count",
                    "following_count",
                    "profile_location",
                    "is_verified",
                ):
                    post["account"][key] = None
        for node in body["nodes"]:
            if node["id"] in self.masked:
                node["region"], node["account_created_at"] = None, None
        sanitized = self.apply(body)
        if not isinstance(sanitized, dict):
            raise TypeError("A campaign must serialize as an object")
        return sanitized


class Exporter:
    def __init__(self, state: StateRepository) -> None:
        self.state = state
        self.repo = state.evidence

    def export(
        self, campaign_id: str, request: ExportRequest, actor: str
    ) -> tuple[EvidenceDossierBundle, str]:
        # Verification precedes all derivative creation. Never catch integrity failures as success.
        verification = self.repo.verify(self.state.scope)
        detail = self.state.get_campaign(campaign_id)
        expected = sha256(canonical_bytes(detail))
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT assessment_hash FROM campaigns WHERE scope=? AND campaign_id=?",
                (self.state.scope, campaign_id),
            ).fetchall()
            retained = self.repo._db.execute(
                "SELECT 1 FROM evidence_artifacts WHERE scope=? AND sha256=? AND kind='ANALYSIS'",
                (self.state.scope, expected),
            ).fetchone()
        if not retained or not any(row[0] == expected for row in rows):
            raise IntegrityMismatch("Campaign snapshot differs from retained analysis")
        transform = PrivacyTransform(detail, request.redact_pii)
        safe = transform.detail(detail)
        safe_summary = NarrativeCampaignSummary.model_validate(
            transform.apply(summary(detail).model_dump(mode="json"))
        )
        now = datetime.now(UTC)
        observation_artifact = stix2.Artifact(
            mime_type="application/json",
            payload_bin=base64.b64encode(canonical_bytes(safe)).decode("ascii"),
            hashes={"SHA-256": sha256(canonical_bytes(safe))},
        )
        observed = stix2.ObservedData(
            first_observed=detail.first_detected_utc,
            last_observed=detail.last_updated_utc,
            number_observed=max(detail.total_posts, 1),
            object_refs=[observation_artifact.id],
        )
        grouping = stix2.Grouping(
            name=transform.text(detail.title),
            context="unspecified",
            object_refs=[observed.id],
            description=f"Observed {detail.data_origin.value}; "
            "coordination indicators do not establish intent.",
        )
        note = stix2.Note(
            content=f"Origin: {detail.data_origin.value}. "
            f"Claim status: {detail.claim_verification.status.value}. "
            f"Parameter set: {self.repo.parameters.parameter_set_id}. "
            "Local hashes do not prove truth or legal admissibility.",
            object_refs=[observed.id, grouping.id],
        )
        relationship = stix2.Relationship(
            relationship_type="related-to", source_ref=grouping.id, target_ref=observed.id
        )
        stix_text = stix2.Bundle(
            objects=[observation_artifact, observed, grouping, note, relationship],
            allow_custom=True,
        ).serialize()
        stix2.parse(stix_text, allow_custom=True)
        stix_json = json.loads(stix_text)
        with self.repo._lock:
            audits = [
                AuditTrailEntry.model_validate_json(row[0])
                for row in self.repo._db.execute(
                    "SELECT entry_json FROM audit_entries ORDER BY sequence"
                )
            ]
        artifacts = []
        files: dict[str, bytes] = {}
        safe_posts = safe["sample_posts"]
        if not isinstance(safe_posts, list):
            raise TypeError("Sanitized posts must remain a list")
        for event, sanitized in zip(detail.sample_posts, safe_posts, strict=True):
            data = (
                canonical_bytes(sanitized)
                if request.redact_pii
                else canonical_bytes(event.model_dump(exclude={"canonical_event_sha256"}))
            )
            with self.repo.transaction() as db:
                artifact_id, digest = self.repo.put_artifact(
                    db, data, "REPORT", "application/json", detail.data_origin, self.state.scope
                )
            artifacts.append(
                EvidenceArtifact(
                    artifact_id=artifact_id,
                    artifact_kind="CANONICAL_EVENT",
                    sha256_hash=digest,
                    evidence_ref=artifact_id,
                    representation="REDACTED_DERIVATIVE" if request.redact_pii else "ORIGINAL",
                    original_sha256=event.canonical_event_sha256 if request.redact_pii else None,
                )
            )
            files[f"observations/{digest}.json"] = data
            if not request.redact_pii:
                for ref in [
                    event.raw_payload_ref,
                    *[
                        media.evidence_ref
                        for media in event.media_attachments
                        if media.evidence_ref
                    ],
                ]:
                    original, mime, kind = self.repo.artifact(ref, self.state.scope)
                    files[f"originals/{sha256(original)}.bin"] = original
        bundle = EvidenceDossierBundle(
            dossier_id=uuid4().hex,
            generated_at_utc=now,
            parameter_set_id=self.repo.parameters.parameter_set_id,
            redacted_pii=request.redact_pii,
            campaign_summary=safe_summary,
            key_coordination_findings=[
                transform.text(reason) for reason in detail.coordination_assessment.evidence_reasons
            ],
            media_forensic_reports=detail.media_reports,
            audit_manifest=audits,
            artifacts=artifacts,
            stix2_bundle_json=stix_json,
        )
        # All representations derive from this one privacy transform.
        files["dossier.json"] = canonical_bytes(bundle)
        files["observations.json"] = canonical_bytes(safe)
        disclaimer = (
            bundle.integrity_disclaimer
            + " Audit manifest is the retained prefix before this export; "
            "the export action remains in the local ledger."
        )
        lines = [
            "CHAKRAVYUH - TAMPER-EVIDENT INVESTIGATIVE DOSSIER",
            transform.text(detail.title),
            f"Origin: {detail.data_origin.value} | Snapshot {detail.snapshot_revision}",
            f"Collection UTC: {detail.first_detected_utc.isoformat()} "
            f"to {detail.last_updated_utc.isoformat()}",
            f"Claim status: {detail.claim_verification.status.value}",
            f"CTI: {display_score(detail.cti_assessment.cti_score)} | "
            f"Synchronization: {display_score(detail.coordination_assessment.sync_score)}",
            f"Posts: {detail.total_posts} | Accounts: {detail.total_accounts}",
            "Method: frozen lexical fallback; ELA/pHash compression indicators. "
            "Null means unavailable.",
            "Claim review: " + transform.text(detail.claim_verification.analyst_note),
            disclaimer,
        ]
        lines += [
            transform.text(event.account.handle + ": " + event.text)
            for event in detail.sample_posts
        ]
        files["report.html"] = (
            "<!doctype html><html lang='en'><meta charset='utf-8'><title>Chakravyuh dossier</title>"
            "<style>body{font:16px sans-serif;max-width:850px;margin:40px auto;"
            "line-height:1.6;padding:20px}"
            "p{overflow-wrap:anywhere}</style><body>"
            + "".join("<p>" + html.escape(line) + "</p>" for line in lines)
            + "</body></html>"
        ).encode()
        files["report.pdf"] = render_pdf(lines)
        files["stix.json"] = canonical_bytes(stix_json)
        files["DISCLAIMER.txt"] = disclaimer.encode()
        if request.format != "bundle":
            keep = {
                "dossier.json",
                "DISCLAIMER.txt",
                {"pdf": "report.pdf", "html": "report.html", "stix": "stix.json"}[request.format],
            }
            files = {name: data for name, data in files.items() if name in keep}
        manifest = {
            "version": "dossier-manifest-v1",
            "redacted_pii": request.redact_pii,
            "verification": verification,
            "campaign_snapshot_sha256": expected,
            "parameter_set_id": self.repo.parameters.parameter_set_id,
            "files": {
                name: {"sha256": sha256(data), "size": len(data)} for name, data in files.items()
            },
            "disclaimer": disclaimer,
        }
        files["manifest.json"] = canonical_bytes(manifest)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                archive.writestr(name, data)
        with self.repo.transaction() as db:
            artifact_id, digest = self.repo.put_artifact(
                db,
                buffer.getvalue(),
                "REPORT",
                "application/zip",
                detail.data_origin,
                self.state.scope,
            )
            self.repo.append_audit(
                db,
                action="EXPORT",
                origin=detail.data_origin,
                actor_id=actor,
                artifact_sha256=[digest],
                verification_status="VERIFIED",
            )
        return bundle, artifact_id


def render_pdf(lines: list[str]) -> bytes:
    fonts = Path(__file__).parent / "fonts"
    if "ChakravyuhSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ChakravyuhSans", str(fonts / "ChakravyuhNoto-Regular.ttf")))
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Chakravyuh investigative dossier",
    )
    style = ParagraphStyle(
        "body",
        fontName="ChakravyuhSans",
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#172033"),
        shaping=True,
        splitLongWords=True,
    )
    story = []
    for index, line in enumerate(lines):
        escaped = html.escape(line)
        paragraph_style = (
            style
            if index
            else ParagraphStyle("title", parent=style, fontSize=16, leading=22, spaceAfter=12)
        )
        story.extend([Paragraph(escaped, paragraph_style), Spacer(1, 6)])
    document.build(story)
    return buffer.getvalue()


def display_score(value: float | None) -> str:
    return "Insufficient data" if value is None else f"{value:.3f}"
