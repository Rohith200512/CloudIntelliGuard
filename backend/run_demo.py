"""CloudIntelliGuard — Automated End-to-End Pipeline Execution Script.
Executes the full workflow: Auth -> Dataset Ingestion -> Temporal Graph -> Model Training -> Anomaly Detection -> Risk & Report.
"""
import sys
import httpx

BASE_URL = "http://127.0.0.1:8001"


def main():
    print("=" * 60)
    print(" CloudIntelliGuard: Phase 1 ML & Anomaly Detection Pipeline")
    print("=" * 60)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health Check
        print("\n[1/6] Checking API server...")
        try:
            r = client.get("/openapi.json")
            r.raise_for_status()
            info = r.json().get("info", {})
            print(f"      Server is ONLINE: {info.get('title')} v{info.get('version')}")
        except Exception as e:
            print(f"      Error connecting to server at {BASE_URL}: {e}")
            sys.exit(1)

        # 2. Authentication
        print("\n[2/6] Authenticating as Admin...")
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "Admin123!"},
        )
        if login_resp.status_code != 200:
            print(f"      Authentication failed: {login_resp.text}")
            sys.exit(1)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("      Authentication SUCCESS (JWT token acquired)")

        # 3. Upload Dataset
        print("\n[3/6] Ingesting CloudTrail demo dataset...")
        csv_path = "data/demo/sample_cloudtrail.csv"
        with open(csv_path, "rb") as f:
            files = {"file": ("sample_cloudtrail.csv", f, "text/csv")}
            upload_resp = client.post(
                "/api/v1/datasets/upload",
                headers=headers,
                files=files,
            )
        upload_resp.raise_for_status()
        ds_data = upload_resp.json()
        dataset_id = ds_data["id"]
        print(f"      Dataset uploaded: ID = {dataset_id}, File = '{ds_data['filename']}', Status = '{ds_data['status']}'")

        # 4. Process Temporal Graph Windows
        print("\n[4/6] Preprocessing and constructing temporal graph windows...")
        proc_resp = client.post(
            f"/api/v1/datasets/{dataset_id}/process",
            headers=headers,
            json={"window_type": "fixed", "window_hours": 24},
        )
        proc_resp.raise_for_status()
        print(f"      Graph construction SUCCESS: {proc_resp.json().get('message')}")

        # 5. Train Model & Run Inference
        print("\n[5/6] Training baseline GCN model and running inference...")
        train_resp = client.post(
            "/api/v1/detection/models/train",
            headers=headers,
            json={"dataset_id": dataset_id, "model_type": "baseline"},
        )
        train_resp.raise_for_status()
        run_data = train_resp.json()
        print(f"      Model trained: Run ID = {run_data['id']}, Status = '{run_data['status']}'")

        infer_resp = client.post(
            "/api/v1/detection/models/infer",
            headers=headers,
            json={
                "graph_window_id": run_data.get("graph_window_id", 1),
                "model_type": "baseline",
                "threshold": 0.5,
            },
        )
        infer_resp.raise_for_status()
        anomalies = infer_resp.json()
        print(f"      Inference complete: Evaluated {len(anomalies)} user nodes")

        print("\n" + "-" * 20 + " User Anomaly Scores " + "-" * 20)
        for a in sorted(anomalies, key=lambda x: x["anomaly_score"], reverse=True):
            flag = "[!] ANOMALY" if a["is_anomaly"] else "[ok] NORMAL "
            print(f"  {flag} -> User: {a['cloud_user_id']:<6} | Anomaly Score: {a['anomaly_score']:.4f}")

        # 6. Dashboard Summary
        print("\n[6/6] Fetching live security dashboard summary...")
        summary_resp = client.get("/api/v1/evaluation/dashboard/summary", headers=headers)
        summary_resp.raise_for_status()
        s = summary_resp.json()
        print(f"      Total Datasets     : {s['total_datasets']}")
        print(f"      Total Events       : {s['total_events']}")
        print(f"      Total Anomalies    : {s['total_anomalies']}")
        print(f"      Open Incidents     : {s['open_incidents']}")
        print(f"      Total Alerts       : {s['total_alerts']}")

        print("\n" + "=" * 60)
        print(" Pipeline Task Execution Completed Successfully!")
        print(f" Interactive Swagger UI: {BASE_URL}/docs")
        print("=" * 60)


if __name__ == "__main__":
    main()
