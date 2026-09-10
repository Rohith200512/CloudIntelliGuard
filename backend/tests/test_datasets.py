"""Tests for dataset ingestion and preprocessing."""
import io
import pytest


SAMPLE_CSV = b"""timestamp,user_id,action,service,resource,source_ip,status
2024-01-15T08:00:00Z,U001,ListBuckets,s3,arn:aws:s3:::test-bucket,10.0.0.1,success
2024-01-15T08:05:00Z,U001,GetObject,s3,arn:aws:s3:::test-bucket/file.txt,10.0.0.1,success
2024-01-15T09:00:00Z,U002,DescribeInstances,ec2,arn:aws:ec2:us-east-1:123:instance/i-001,10.0.0.2,success
2024-01-15T09:05:00Z,U002,DescribeInstances,ec2,arn:aws:ec2:us-east-1:123:instance/i-002,10.0.0.2,failure
"""

MINIMAL_CSV = b"""timestamp,user_id
2024-01-15T08:00:00Z,U001
2024-01-15T09:00:00Z,U002
"""


@pytest.mark.asyncio
async def test_upload_csv(client, auth_headers):
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        files={"file": ("test.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_type"] == "csv"
    assert data["status"] == "UPLOADED"
    assert data["raw_event_count"] == 4


@pytest.mark.asyncio
async def test_upload_minimal_csv(client, auth_headers):
    """CSV with only required columns should succeed."""
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        files={"file": ("minimal.csv", io.BytesIO(MINIMAL_CSV), "text/csv")},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_upload_missing_timestamp(client, auth_headers):
    """CSV missing the timestamp column should be rejected."""
    bad_csv = b"user_id,action\nU001,GetObject\n"
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        files={"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_datasets(client, auth_headers):
    resp = await client.get("/api/v1/datasets", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_process_dataset(client, auth_headers):
    # First upload
    up = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        files={"file": ("proc_test.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert up.status_code == 201
    dataset_id = up.json()["id"]

    # Then process
    resp = await client.post(
        f"/api/v1/datasets/{dataset_id}/process",
        headers=auth_headers,
        json={"window_type": "fixed", "window_hours": 24},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "windows_created" in data["detail"]
