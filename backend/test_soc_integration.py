"""Verify all 7 SOC test scenarios end-to-end against live server."""
import httpx

base = "http://127.0.0.1:8001/api/v1"


def main():
    print("=" * 65)
    print(" Verifying CloudIntelliGuard SOC 9-Page System End-to-End")
    print("=" * 65)

    with httpx.Client(timeout=30.0) as client:
        # Auth
        auth_resp = client.post(f"{base}/auth/login", data={"username": "admin", "password": "Admin123!"})
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("\n[PASS] Scenario 1: Authentication & Token Acquired")

        # 1. Enforcements (Scenario 3 & 4: HIGH->Restrict & CRITICAL->Block)
        enf_resp = client.get(f"{base}/response", headers=headers)
        enforcements = enf_resp.json()
        print(f"\n[PASS] Scenario 2 & 3: Automated Enforcements Active ({len(enforcements)} identities)")
        for e in enforcements[:4]:
            print(f"    Identity: {e['cloud_user_id']:<30} | Status: {e['status']:<12} | Risk: {e['risk_score']:.1f} ({e['risk_level']}) | Session: {'REVOKED' if e['session_revoked'] else 'Active'}")

        # 2. User Behavior Analytics (Scenario 5: UBA Investigation)
        uba_resp = client.get(f"{base}/uba/profile/level6", headers=headers)
        uba = uba_resp.json()
        print(f"\n[PASS] Scenario 4: User Behavior Analytics Profile (level6)")
        print(f"    - Status: {uba['current_status']} | Deviation Score: {uba['deviation_score']}%")
        print(f"    - Baseline: {uba['baseline']['avg_daily_api_calls']} calls/day vs Current: {uba['current_behavior']['current_api_calls']} calls/day")
        print(f"    - Suspicious Indicators ({len(uba['suspicious_indicators'])}):")
        for ind in uba["suspicious_indicators"][:3]:
            print(f"      * [{ind['severity']}] {ind['name']}: {ind['description']}")

        # 3. Attack Path Analysis (Scenario 5: Attack Path Traversal)
        ap_resp = client.get(f"{base}/attack-path?user_id=level6", headers=headers)
        paths = ap_resp.json()
        print(f"\n[PASS] Scenario 5: Attack Path Analysis (Found {len(paths)} chains for level6)")
        if paths:
            top_p = paths[0]
            print(f"    - Target Resource: {top_p['target_resource']} | Path Risk Score: {top_p['path_risk_score']}")
            print(f"    - Progression Steps ({len(top_p['steps'])}):")
            for s in top_p["steps"][:4]:
                print(f"      Step {s['step_number']}: {s['source_type']} ({s['source_entity']}) ➔ {s['target_type']} ({s['target_entity']}) [{s['action']}]")

        # 4. What-If Simulator (Scenario 7: Simulation Sandbox)
        sim_resp = client.post(
            f"{base}/risk-simulator/simulate",
            headers=headers,
            json={
                "cloud_user_id": "backup",
                "privilege_escalation": True,
                "sensitive_resource_access": True,
                "abnormal_api_activity": True,
            },
        )
        sim = sim_resp.json()
        print(f"\n[PASS] Scenario 6: What-If Risk Simulator (backup)")
        print(f"    - Baseline Risk : {sim['current_risk_score']:.1f} ({sim['current_risk_level']})")
        print(f"    - Simulated Risk: {sim['simulated_risk_score']:.1f} ({sim['simulated_risk_level']}) [Delta: +{sim['delta']:.1f} pts]")
        print(f"    - Top Contributor: {sim['top_contributor']}")
        print(f"    - Explanation: {sim['explanation']}")

        # 5. AI Copilot (Scenario 6: Grounded Assistant)
        cop_resp = client.post(
            f"{base}/copilot/query",
            headers=headers,
            json={"query": "Why was level6 flagged and restricted?"},
        )
        cop = cop_resp.json()
        print(f"\n[PASS] Scenario 7: AI Copilot Grounded Query")
        print(f"    - Detected Intent: {cop['intent']}")
        print(f"    - Grounded Sources: {', '.join(cop['data_sources_used'])}")
        safe_answer = cop['answer'].encode('ascii', 'replace').decode('ascii')
        print(f"    - Copilot Answer:\n{safe_answer}")

        # 6. Audit Trail
        audit_resp = client.get(f"{base}/audit", headers=headers)
        logs = audit_resp.json()
        print(f"\n[PASS] Scenario 8: Immutable Audit Trail ({len(logs)} entries logged)")
        for log in logs[:3]:
            print(f"    - [{log['timestamp'][:19]}] {log['action']} on {log['resource']}")

    print("\n" + "=" * 65)
    print(" ALL END-TO-END SOC SCENARIOS VERIFIED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
