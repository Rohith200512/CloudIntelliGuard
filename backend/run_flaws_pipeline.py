"""CloudIntelliGuard — Execute Pipeline on Cleaned FlAWS Real-World Dataset."""
import httpx
import sys

BASE_URL = "http://127.0.0.1:8001"


def main():
    print("=" * 65)
    print(" CloudIntelliGuard: Running Cleaned Real-World FlAWS Dataset")
    print("=" * 65)

    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        # 1. Authenticate
        print("\n[1/6] Authenticating as Admin...")
        try:
            login = client.post("/api/v1/auth/login", data={"username": "admin", "password": "Admin123!"})
            login.raise_for_status()
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("      Authentication SUCCESS")
        except Exception as e:
            print(f"      Error: {e}")
            sys.exit(1)

        # 2. Ingest Dataset
        dataset_file = "data/processed/flaws_cloudtrail_sample_10k.csv"
        print(f"\n[2/6] Ingesting cleaned dataset ({dataset_file})...")
        with open(dataset_file, "rb") as f:
            upload = client.post(
                "/api/v1/datasets/upload",
                headers=headers,
                files={"file": ("flaws_cloudtrail_sample_10k.csv", f, "text/csv")},
            )
        upload.raise_for_status()
        ds = upload.json()
        ds_id = ds["id"]
        print(f"      Dataset Uploaded: ID = #{ds_id}, Name = '{ds['filename']}', Raw Events = {ds['raw_event_count']:,}")

        # 3. Construct Temporal Graph Windows
        print("\n[3/6] Preprocessing and constructing temporal dynamic graph windows...")
        proc = client.post(
            f"/api/v1/datasets/{ds_id}/process",
            headers=headers,
            json={"window_type": "fixed", "window_hours": 24},
        )
        proc.raise_for_status()
        print(f"      Graph Construction SUCCESS: {proc.json().get('message')}")

        # 4. Train Model
        print("\n[4/6] Training Baseline GCN + IsolationForest Anomaly Model...")
        train = client.post(
            "/api/v1/detection/models/train",
            headers=headers,
            json={"dataset_id": ds_id, "model_type": "baseline"},
        )
        train.raise_for_status()
        model_run = train.json()
        print(f"      Model Trained: Run ID = #{model_run['id']}, Status = '{model_run['status']}'")

        # 5. Run Inference
        gw_id = model_run.get("graph_window_id") or ds_id
        print(f"\n[5/6] Running inference on Graph Window #{gw_id} (threshold = 0.50)...")
        infer = client.post(
            "/api/v1/detection/models/infer",
            headers=headers,
            json={"graph_window_id": gw_id, "model_type": "baseline", "threshold": 0.5},
        )
        infer.raise_for_status()
        anomalies = infer.json()
        print(f"      Inference Complete: Evaluated {len(anomalies)} IAM identities")

        print("\n" + "-" * 25 + " Evaluated IAM Anomaly Scores " + "-" * 25)
        for a in sorted(anomalies, key=lambda x: x["anomaly_score"], reverse=True):
            status_flag = "[!] ANOMALOUS" if a["is_anomaly"] else "[ok] NORMAL   "
            score_pct = a["anomaly_score"] * 100
            print(f"  {status_flag}  Identity: {a['cloud_user_id']:<38} | Score: {score_pct:.2f}%")

        # 6. Live Dashboard Summary
        print("\n[6/6] Fetching updated security telemetry summary...")
        dash = client.get("/api/v1/evaluation/dashboard/summary", headers=headers).json()
        print(f"      Total Datasets  : {dash['total_datasets']}")
        print(f"      Total Events    : {dash['total_events']:,}")
        print(f"      Total Anomalies : {dash['total_anomalies']}")
        print(f"      Open Incidents  : {dash['open_incidents']}")
        print(f"      Total Alerts    : {dash['total_alerts']}")

        print("\n" + "=" * 65)
        print(" Dataset Execution Completed Successfully!")
        print(" Explore interactive visualizations at: http://127.0.0.1:5173")
        print("=" * 65)


if __name__ == "__main__":
    main()
