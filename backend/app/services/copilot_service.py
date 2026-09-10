"""
AI Copilot Security Assistant Service — CloudIntelliGuard.

Grounds natural language SOC queries into actual live database telemetry:
  - Incident context & explanations
  - User risk & behavioral deviations
  - Autonomous enforcement actions & reasons
  - Attack path traversals
"""
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import (
    Anomaly, AuditLog, CloudEvent, CloudUserEnforcement, Incident, RiskScore,
)
from app.services.attack_path_service import get_attack_paths
from app.services.uba_service import compute_user_uba_profile


async def answer_copilot_query(
    db: AsyncSession,
    query: str,
    context_user_id: Optional[str] = None,
    context_incident_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Process analyst query and return factual, grounded response using database state.
    """
    q = query.lower().strip()
    data_sources = []
    related_entities = []
    suggested_actions = []

    # Extract user ID mention if present (e.g. "level6", "user_104", "backup", "root", etc.)
    user_match = None
    # Check existing users in DB
    enf_res = await db.execute(select(CloudUserEnforcement))
    all_enfs = enf_res.scalars().all()
    user_map = {e.cloud_user_id.lower(): e for e in all_enfs}

    for u_lower, enf in user_map.items():
        if u_lower in q or (context_user_id and u_lower == context_user_id.lower()):
            user_match = enf
            break

    # Intent 1: "Highest risk" / "Top threats"
    if "highest risk" in q or "top threat" in q or "most dangerous" in q or "highest threat" in q:
        data_sources.append("cloud_user_enforcements")
        data_sources.append("risk_scores")

        top_users = sorted(all_enfs, key=lambda x: x.risk_score, reverse=True)[:5]
        if not top_users:
            answer = "No evaluated cloud identities currently found in the system. Ingest a dataset and run inference to populate risk scores."
        else:
            top_user = top_users[0]
            lines = [f"**Highest Risk Identity:** `{top_user.cloud_user_id}` with a Risk Score of **{top_user.risk_score:.1f}/100** ({top_user.risk_level})."]
            lines.append(f"**Current Status:** `{top_user.status}`")
            if top_user.blocking_reason:
                lines.append(f"**Block Reason:** {top_user.blocking_reason}")
            elif top_user.restriction_reason:
                lines.append(f"**Restriction Reason:** {top_user.restriction_reason}")

            lines.append("\n**Top Monitored Identities by Risk:**")
            for u in top_users:
                lines.append(f"- `{u.cloud_user_id}`: Risk **{u.risk_score:.1f}** ({u.risk_level}) — Status: **{u.status}**")

            answer = "\n".join(lines)
            related_entities.append({"type": "USER", "id": top_user.cloud_user_id, "risk": top_user.risk_score})
            suggested_actions.extend([
                f"View Attack Path for {top_user.cloud_user_id}",
                f"Inspect User Behavior Profile for {top_user.cloud_user_id}",
                "Review Automated Response Enforcements",
            ])

        return {
            "query": query,
            "answer": answer,
            "intent": "QUERY_HIGHEST_RISK",
            "related_entities": related_entities,
            "suggested_actions": suggested_actions,
            "data_sources_used": data_sources,
        }

    # Intent 2: "Why was [user] flagged / restricted / blocked?"
    if ("why" in q and ("flagged" in q or "blocked" in q or "restricted" in q or "anomaly" in q)) or (user_match and ("why" in q or "detail" in q or "tell me about" in q or "status" in q)):
        target_uid = user_match.cloud_user_id if user_match else (context_user_id or "level6")
        data_sources.extend(["cloud_user_enforcements", "anomalies", "uba_profile", "audit_logs"])

        # Fetch UBA & Anomaly details
        uba = await compute_user_uba_profile(db, target_uid)
        anom_res = await db.execute(
            select(Anomaly).where(Anomaly.cloud_user_id == target_uid).order_by(Anomaly.created_at.desc())
        )
        anom = anom_res.scalars().first()

        lines = [f"### 🛡️ Analysis for Identity: `{target_uid}`"]
        lines.append(f"- **Current Status:** `{uba['current_status']}` | **Risk Score:** `{uba['current_risk_score']:.1f}/100` ({uba['current_risk_level']})")
        lines.append(f"- **Behavioral Deviation Score:** `{uba['deviation_score']:.1f}/100`")

        if user_match and user_match.session_revoked:
            lines.append(f"- **Enforcement:** 🚨 **ACTIVE CREDENTIAL / SESSION REVOKED** ({user_match.blocking_reason or 'Critical Threat'})")
        elif user_match and user_match.status == "RESTRICTED":
            lines.append(f"- **Enforcement:** ⚠️ **QUARANTINED** ({user_match.restriction_reason or 'High Privilege Anomaly'})")

        if uba["suspicious_indicators"]:
            lines.append("\n**Key Suspicious Indicators Detected:**")
            for ind in uba["suspicious_indicators"]:
                lines.append(f"- **[{ind['severity']}] {ind['name']}:** {ind['description']}")

        if anom and anom.explanation:
            summary = anom.explanation.get("summary")
            if summary:
                lines.append(f"\n**GNN Anomaly Explanation:** {summary}")

        answer = "\n".join(lines)
        related_entities.append({"type": "USER", "id": target_uid, "risk": uba["current_risk_score"]})
        suggested_actions.extend([
            f"Launch Attack Path for {target_uid}",
            f"Run What-If Simulation for {target_uid}",
            "View Full UBA Profile",
        ])

        return {
            "query": query,
            "answer": answer,
            "intent": "QUERY_USER_EXPLANATION",
            "related_entities": related_entities,
            "suggested_actions": suggested_actions,
            "data_sources_used": data_sources,
        }

    # Intent 3: "Attack path"
    if "attack path" in q or "kill chain" in q or "path" in q:
        data_sources.append("attack_paths")
        target_uid = user_match.cloud_user_id if user_match else (context_user_id or None)
        paths = await get_attack_paths(db, cloud_user_id=target_uid)

        if not paths:
            answer = "No suspicious attack paths currently detected. All observed graph transitions are within normal baseline thresholds."
        else:
            top_p = paths[0]
            lines = [f"### ⚔️ Attack Path Analysis for `{top_p['cloud_user_id']}` (Risk: {top_p['path_risk_score']:.1f})"]
            lines.append(f"**Target Resource:** `{top_p['target_resource']}`\n")
            lines.append("**Progression Sequence:**")
            for s in top_p["steps"]:
                warn = "⚠️" if s["is_suspicious"] else "➡️"
                lines.append(f"{s['step_number']}. {warn} **{s['source_type']}** `{s['source_entity']}` ➔ **{s['target_type']}** `{s['target_entity']}` ({s['action']})")

            answer = "\n".join(lines)
            related_entities.append({"type": "ATTACK_PATH", "id": top_p["path_id"], "user": top_p["cloud_user_id"]})
            suggested_actions.extend([
                "Open Attack Path Visualizer",
                "Quarantine Intermediate Service",
            ])

        return {
            "query": query,
            "answer": answer,
            "intent": "QUERY_ATTACK_PATH",
            "related_entities": related_entities,
            "suggested_actions": suggested_actions,
            "data_sources_used": data_sources,
        }

    # Intent 4: "Critical incidents" / "Active incidents"
    if "incident" in q or "critical" in q or "active alerts" in q:
        data_sources.append("incidents")
        inc_res = await db.execute(select(Incident).order_by(Incident.created_at.desc()).limit(5))
        incidents = inc_res.scalars().all()

        if not incidents:
            answer = "There are currently 0 active critical security incidents."
        else:
            lines = [f"**Found {len(incidents)} Recent Security Incident(s):**\n"]
            for inc in incidents:
                lines.append(f"- **Incident #{inc.id} [{inc.severity} / {inc.status}]:** {inc.title}")
                if inc.explanation:
                    lines.append(f"  *Detail:* {inc.explanation[:120]}...")
            answer = "\n".join(lines)
            suggested_actions.extend(["Review Incident Triage Console", "Inspect Automated Responses"])

        return {
            "query": query,
            "answer": answer,
            "intent": "QUERY_INCIDENTS",
            "related_entities": related_entities,
            "suggested_actions": suggested_actions,
            "data_sources_used": data_sources,
        }

    # Intent 5: "Automated action" / "What was done"
    if "action" in q or "automated" in q or "response" in q or "blocked" in q:
        data_sources.extend(["audit_logs", "cloud_user_enforcements"])
        audit_res = await db.execute(
            select(AuditLog).where(AuditLog.action.like("%AUTOMATED%")).order_by(AuditLog.timestamp.desc()).limit(5)
        )
        logs = audit_res.scalars().all()

        if not logs:
            answer = "No automated restrictions or blocks have been triggered yet. When a user's risk exceeds 50 (HIGH) or 75 (CRITICAL), the autonomous policy engine executes immediately."
        else:
            lines = ["**Recent Autonomous Response Actions:**\n"]
            for log in logs:
                u_res = log.resource or "N/A"
                detail = log.detail or {}
                reason = detail.get("reason", "Risk policy threshold breached")
                lines.append(f"- **{log.action}** on `{u_res}` at {log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                lines.append(f"  *Reason:* {reason}")
            answer = "\n".join(lines)

        return {
            "query": query,
            "answer": answer,
            "intent": "QUERY_AUTOMATED_ACTIONS",
            "related_entities": related_entities,
            "suggested_actions": ["View Audit Log", "Inspect Enforcements Table"],
            "data_sources_used": data_sources,
        }

    # Default general assistance
    data_sources.append("cloud_telemetry_index")
    answer = (
        f"CloudIntelliGuard AI Copilot is monitoring your cloud environment. "
        f"You can ask me questions like:\n"
        f"- *'Why was level6 flagged?'*\n"
        f"- *'Which user currently has the highest risk?'*\n"
        f"- *'Show the attack path for the latest incident.'*\n"
        f"- *'What automated actions were taken?'*\n"
        f"- *'Which incidents are critical?'*"
    )
    return {
        "query": query,
        "answer": answer,
        "intent": "GENERAL_QUERY",
        "related_entities": related_entities,
        "suggested_actions": ["Show Top Risk Users", "Show Critical Incidents", "Explain level6 Activity"],
        "data_sources_used": data_sources,
    }
