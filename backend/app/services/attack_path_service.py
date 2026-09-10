"""
Attack Path Analysis Service — CloudIntelliGuard.

Traces multi-hop suspicious event sequences across cloud entities:
  User → IP → Action (Privilege Escalation / Recon) → Service → Sensitive Resource
"""
from typing import Any, Dict, List, Optional
import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import CloudEvent, GraphWindow, Incident
from app.services.feature_engineering import SENSITIVE_SERVICES, SENSITIVE_RESOURCES_PATTERNS
from app.services.graph_builder import deserialize_graph, NODE_USER, NODE_IP, NODE_ACTION, NODE_SERVICE, NODE_RESOURCE

SUSPICIOUS_ACTIONS = {
    "assumerole", "getsessiontoken", "createrole", "putuserpolicy",
    "attachuserpolicy", "createaccesskey", "getsecretvalue", "decrypt",
    "listbuckets", "getcalleridentity", "describekey", "getpassworddata",
    "authorizesecuritygroupingress", "createuser", "updatelogingenerated",
}


async def get_attack_paths(
    db: AsyncSession,
    cloud_user_id: Optional[str] = None,
    target_resource: Optional[str] = None,
    graph_window_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Extract and structure attack paths from graph windows and event sequences.
    """
    # 1. Fetch events
    stmt = select(CloudEvent).order_by(CloudEvent.timestamp.asc())
    if cloud_user_id:
        stmt = stmt.where(CloudEvent.cloud_user_id == cloud_user_id)
    
    events_res = await db.execute(stmt.limit(1000))
    events = events_res.scalars().all()

    if not events:
        return []

    # Group events by user
    user_events: Dict[str, List[CloudEvent]] = {}
    for ev in events:
        uid = ev.cloud_user_id or "unknown"
        if uid not in user_events:
            user_events[uid] = []
        user_events[uid].append(ev)

    attack_paths: List[Dict[str, Any]] = []

    for uid, ev_list in user_events.items():
        if cloud_user_id and uid != cloud_user_id:
            continue

        # Look for sequences that touch sensitive APIs or errors
        suspicious_events = []
        for ev in ev_list:
            act = str(ev.action or "").lower()
            svc = str(ev.service or "").lower()
            res = str(ev.resource or "").lower()
            status = str(ev.status or "").lower()

            is_suspicious = (
                act in SUSPICIOUS_ACTIONS or
                svc in SENSITIVE_SERVICES or
                any(p in res for p in SENSITIVE_RESOURCES_PATTERNS) or
                "fail" in status or "denied" in status or "unauth" in status
            )

            if is_suspicious or len(suspicious_events) < 4:
                suspicious_events.append((ev, is_suspicious))

        if not suspicious_events:
            continue

        # Build chronological multi-hop steps
        steps = []
        step_num = 1
        path_score = 15.0

        for ev, is_susp in suspicious_events[-6:]:  # Focus on key steps
            ip_val = ev.source_ip or "127.0.0.1"
            act_val = ev.action or "APIRequest"
            svc_val = ev.service or "AWS"
            res_val = ev.resource or f"arn:aws:{svc_val}:::default"
            ts_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%SZ") if ev.timestamp else "N/A"

            # Step 1: User -> IP
            if step_num == 1:
                steps.append({
                    "step_number": step_num,
                    "source_entity": uid,
                    "source_type": "USER",
                    "target_entity": ip_val,
                    "target_type": "IP_ADDRESS",
                    "action": "Authenticate / Session Origination",
                    "timestamp": ts_str,
                    "status": "Success",
                    "is_suspicious": False,
                    "details": f"User initialized session from {ip_val}",
                })
                step_num += 1

            # Step 2: IP -> Action
            steps.append({
                "step_number": step_num,
                "source_entity": ip_val,
                "source_type": "IP_ADDRESS",
                "target_entity": act_val,
                "target_type": "ACTION",
                "action": f"Invoke {act_val}",
                "timestamp": ts_str,
                "status": ev.status or "Success",
                "is_suspicious": is_susp,
                "details": f"API call '{act_val}' executed via {svc_val}",
            })
            step_num += 1

            # Step 3: Action -> Service
            steps.append({
                "step_number": step_num,
                "source_entity": act_val,
                "source_type": "ACTION",
                "target_entity": svc_val,
                "target_type": "SERVICE",
                "action": f"Target Service {svc_val}",
                "timestamp": ts_str,
                "status": ev.status or "Success",
                "is_suspicious": svc_val.lower() in SENSITIVE_SERVICES,
                "details": f"Targeted service endpoint {svc_val}",
            })
            step_num += 1

            # Step 4: Service -> Target Resource
            steps.append({
                "step_number": step_num,
                "source_entity": svc_val,
                "source_type": "SERVICE",
                "target_entity": res_val,
                "target_type": "RESOURCE",
                "action": "Resource Mutation / Read",
                "timestamp": ts_str,
                "status": ev.status or "Success",
                "is_suspicious": any(p in res_val.lower() for p in SENSITIVE_RESOURCES_PATTERNS),
                "details": f"Access attempted on resource: {res_val}",
            })
            step_num += 1

            if is_susp:
                path_score += 15.0

        path_score = round(min(100.0, path_score), 1)
        severity = "CRITICAL" if path_score >= 75 else "HIGH" if path_score >= 50 else "MEDIUM" if path_score >= 25 else "LOW"

        target_res_label = steps[-1]["target_entity"] if steps else "N/A"
        summary = (
            f"Multi-hop attack path for identity '{uid}': originated from IP {steps[0]['target_entity'] if steps else 'N/A'}, "
            f"progressed through {len(steps)} entity interactions, reaching target resource {target_res_label}."
        )

        attack_paths.append({
            "path_id": f"ap_{uid}_{len(steps)}",
            "cloud_user_id": uid,
            "target_resource": target_res_label,
            "path_risk_score": path_score,
            "severity": severity,
            "steps": steps,
            "summary": summary,
        })

    return sorted(attack_paths, key=lambda x: x["path_risk_score"], reverse=True)
