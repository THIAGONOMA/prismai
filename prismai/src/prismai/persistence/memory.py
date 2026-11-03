from __future__ import annotations

import copy
from datetime import datetime, timezone


class InMemoryRepository:
    def __init__(self) -> None:
        self._reviews: dict[str, dict] = {}
        self._protocols: dict[str, dict] = {}
        self._records: dict[str, list[dict]] = {}
        self._decisions: dict[str, list[dict]] = {}
        self._conflicts: dict[str, list[dict]] = {}
        self._documents: dict[str, list[dict]] = {}
        self._eligibility_decisions: dict[str, list[dict]] = {}
        self._evidence_spans: dict[str, list[dict]] = {}
        self._traces: dict[str, list[dict]] = {}
        self._extraction_schemas: dict[str, dict] = {}
        self._extractions: dict[str, list[dict]] = {}
        self._rob_assessments: dict[str, list[dict]] = {}
        self._synthesis_configs: dict[str, dict] = {}
        self._syntheses: dict[str, list[dict]] = {}
        self._grade_assessments: dict[str, list[dict]] = {}
        self._import_runs: dict[str, list[dict]] = {}
        self._reports: dict[str, list[dict]] = {}
        self._living_updates: dict[str, list[dict]] = {}

    async def create_review(self, review_id: str) -> dict:
        if review_id in self._reviews:
            raise ValueError(f"Review '{review_id}' already exists")
        review = {"id": review_id, "created_at": datetime.now(timezone.utc).isoformat()}
        self._reviews[review_id] = review
        self._records[review_id] = []
        self._decisions[review_id] = []
        self._conflicts[review_id] = []
        self._traces[review_id] = []
        return copy.deepcopy(review)

    async def get_review(self, review_id: str) -> dict | None:
        r = self._reviews.get(review_id)
        return copy.deepcopy(r) if r else None

    async def set_protocol(self, review_id: str, protocol: dict) -> None:
        self._ensure_review(review_id)
        self._protocols[review_id] = copy.deepcopy(protocol)

    async def get_protocol(self, review_id: str) -> dict | None:
        p = self._protocols.get(review_id)
        return copy.deepcopy(p) if p else None

    async def add_records(self, review_id: str, records: list[dict]) -> int:
        self._ensure_review(review_id)
        self._records[review_id].extend(copy.deepcopy(records))
        return len(records)

    async def get_records(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._records.get(review_id, []))

    async def add_decision(self, review_id: str, decision: dict, screener: str = "primary") -> None:
        self._ensure_review(review_id)
        d = copy.deepcopy(decision)
        d["screener"] = screener
        self._decisions[review_id].append(d)

    async def get_decisions(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._decisions.get(review_id, []))

    async def get_decided_registro_ids(self, review_id: str, screener: str | None = None) -> set[str]:
        decisions = self._decisions.get(review_id, [])
        if screener is not None:
            return {d["registro_id"] for d in decisions if d.get("screener") == screener}
        return {d["registro_id"] for d in decisions}

    async def add_conflict(self, review_id: str, conflict: dict) -> None:
        self._ensure_review(review_id)
        self._conflicts[review_id].append(copy.deepcopy(conflict))

    async def get_conflicts(self, review_id: str, status: str | None = None) -> list[dict]:
        conflicts = self._conflicts.get(review_id, [])
        if status is not None:
            conflicts = [c for c in conflicts if c.get("status") == status]
        result = sorted(conflicts, key=lambda c: c.get("disagreement_score", 0), reverse=True)
        return copy.deepcopy(result)

    async def resolve_conflict(self, review_id: str, registro_id: str, decision: str, note: str) -> None:
        self._ensure_review(review_id)
        for c in self._conflicts.get(review_id, []):
            if c["registro_id"] == registro_id:
                c["status"] = "resolved"
                c["resolved_decision"] = decision
                c["resolved_note"] = note
                c["resolved_at"] = datetime.now(timezone.utc).isoformat()
                return
        raise KeyError(f"Conflict for registro '{registro_id}' not found")

    async def add_document(self, review_id: str, document: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._documents:
            self._documents[review_id] = []
        self._documents[review_id].append(copy.deepcopy(document))

    async def get_document(self, review_id: str, record_id: str) -> dict | None:
        for d in self._documents.get(review_id, []):
            if d.get("record_id") == record_id:
                return copy.deepcopy(d)
        return None

    async def get_documents(self, review_id: str, status: str | None = None) -> list[dict]:
        docs = self._documents.get(review_id, [])
        if status is not None:
            docs = [d for d in docs if d.get("status") == status]
        return copy.deepcopy(docs)

    async def update_document(self, review_id: str, record_id: str, updates: dict) -> None:
        self._ensure_review(review_id)
        for d in self._documents.get(review_id, []):
            if d.get("record_id") == record_id:
                d.update(updates)
                return
        raise KeyError(f"Document for record '{record_id}' not found")

    async def add_eligibility_decision(self, review_id: str, decision: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._eligibility_decisions:
            self._eligibility_decisions[review_id] = []
        self._eligibility_decisions[review_id].append(copy.deepcopy(decision))

    async def get_eligibility_decisions(self, review_id: str) -> list[dict]:
        decs = copy.deepcopy(self._eligibility_decisions.get(review_id, []))
        for d in decs:
            if "record_id" not in d:
                d["record_id"] = d.get("document_id", "")
        return decs

    async def add_evidence_span(self, review_id: str, span: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._evidence_spans:
            self._evidence_spans[review_id] = []
        self._evidence_spans[review_id].append(copy.deepcopy(span))

    async def get_evidence_spans(self, review_id: str, record_id: str | None = None) -> list[dict]:
        spans = self._evidence_spans.get(review_id, [])
        if record_id is not None:
            spans = [s for s in spans if s.get("record_id") == record_id]
        return copy.deepcopy(spans)

    async def set_extraction_schema(self, review_id: str, schema: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._protocols:
            raise KeyError(f"Protocol not set for review '{review_id}'")
        self._extraction_schemas[review_id] = copy.deepcopy(schema)

    async def get_extraction_schema(self, review_id: str) -> dict | None:
        s = self._extraction_schemas.get(review_id)
        return copy.deepcopy(s) if s else None

    async def add_extraction(self, review_id: str, extraction: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._extractions:
            self._extractions[review_id] = []
        self._extractions[review_id].append(copy.deepcopy(extraction))

    async def get_extraction(self, review_id: str, record_id: str) -> dict | None:
        for e in self._extractions.get(review_id, []):
            if e.get("record_id") == record_id:
                return copy.deepcopy(e)
        return None

    async def get_extractions(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._extractions.get(review_id, []))

    async def add_rob_assessment(self, review_id: str, assessment: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._rob_assessments:
            self._rob_assessments[review_id] = []
        self._rob_assessments[review_id].append(copy.deepcopy(assessment))

    async def get_rob_assessments(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._rob_assessments.get(review_id, []))

    async def set_synthesis_config(self, review_id: str, config: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._protocols:
            raise KeyError(f"Protocol not set for review '{review_id}'")
        self._synthesis_configs[review_id] = copy.deepcopy(config)

    async def get_synthesis_config(self, review_id: str) -> dict | None:
        s = self._synthesis_configs.get(review_id)
        return copy.deepcopy(s) if s else None

    async def add_synthesis(self, review_id: str, synthesis: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._syntheses:
            self._syntheses[review_id] = []
        self._syntheses[review_id].append(copy.deepcopy(synthesis))

    async def get_synthesis(self, review_id: str, outcome_key: str) -> dict | None:
        for s in self._syntheses.get(review_id, []):
            if s.get("outcome_key") == outcome_key:
                return copy.deepcopy(s)
        return None

    async def get_syntheses(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._syntheses.get(review_id, []))

    async def approve_synthesis(self, review_id: str, outcome_key: str, approved_by: str) -> None:
        self._ensure_review(review_id)
        for s in self._syntheses.get(review_id, []):
            if s.get("outcome_key") == outcome_key:
                s["status"] = "approved"
                s["approved_by"] = approved_by
                s["approved_at"] = datetime.now(timezone.utc).isoformat()
                return
        raise KeyError(f"Synthesis for outcome '{outcome_key}' not found")

    async def add_grade_assessment(self, review_id: str, assessment: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._grade_assessments:
            self._grade_assessments[review_id] = []
        self._grade_assessments[review_id].append(copy.deepcopy(assessment))

    async def get_grade_assessments(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._grade_assessments.get(review_id, []))

    async def approve_grade(self, review_id: str, outcome_key: str, approved_by: str) -> None:
        self._ensure_review(review_id)
        for g in self._grade_assessments.get(review_id, []):
            if g.get("outcome_key") == outcome_key:
                g["status"] = "approved"
                g["approved_by"] = approved_by
                g["approved_at"] = datetime.now(timezone.utc).isoformat()
                return
        raise KeyError(f"GRADE assessment for outcome '{outcome_key}' not found")

    async def add_trace(self, review_id: str, trace: dict) -> None:
        self._ensure_review(review_id)
        self._traces[review_id].append(copy.deepcopy(trace))

    async def get_traces(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._traces.get(review_id, []))

    async def add_import_run(self, review_id: str, run: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._import_runs:
            self._import_runs[review_id] = []
        self._import_runs[review_id].append(copy.deepcopy(run))

    async def get_import_runs(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._import_runs.get(review_id, []))

    async def add_report(self, review_id: str, report: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._reports:
            self._reports[review_id] = []
        existing = [r for r in self._reports[review_id] if r.get("kind") == report.get("kind", "prisma")]
        if existing:
            idx = self._reports[review_id].index(existing[0])
            self._reports[review_id][idx] = copy.deepcopy(report)
        else:
            self._reports[review_id].append(copy.deepcopy(report))

    async def get_report(self, review_id: str, kind: str = "prisma") -> dict | None:
        for r in self._reports.get(review_id, []):
            if r.get("kind") == kind:
                return copy.deepcopy(r)
        return None

    async def approve_report(self, review_id: str, kind: str, approved_by: str) -> None:
        self._ensure_review(review_id)
        for r in self._reports.get(review_id, []):
            if r.get("kind") == kind:
                r["status"] = "approved"
                r["approved_by"] = approved_by
                r["approved_at"] = datetime.now(timezone.utc).isoformat()
                return
        raise KeyError(f"Report kind '{kind}' not found for review '{review_id}'")

    async def enable_living(self, review_id: str, cron_expr: str) -> None:
        self._ensure_review(review_id)
        self._reviews[review_id]["living_enabled"] = True
        self._reviews[review_id]["living_cron"] = cron_expr

    async def disable_living(self, review_id: str) -> None:
        self._ensure_review(review_id)
        self._reviews[review_id]["living_enabled"] = False

    async def add_living_update(self, review_id: str, update: dict) -> None:
        self._ensure_review(review_id)
        if review_id not in self._living_updates:
            self._living_updates[review_id] = []
        self._living_updates[review_id].append(copy.deepcopy(update))
        self._reviews[review_id]["living_last_run_at"] = datetime.now(timezone.utc).isoformat()

    async def get_living_updates(self, review_id: str) -> list[dict]:
        return copy.deepcopy(self._living_updates.get(review_id, []))

    async def get_living_reviews(self) -> list[dict]:
        return [
            {"id": rid, "living_cron": r.get("living_cron"), "living_last_run_at": r.get("living_last_run_at")}
            for rid, r in self._reviews.items()
            if r.get("living_enabled")
        ]

    async def list_reviews(self) -> list[dict]:
        return [copy.deepcopy(r) for r in self._reviews.values()]

    def _ensure_review(self, review_id: str) -> None:
        if review_id not in self._reviews:
            raise KeyError(f"Review '{review_id}' not found")
