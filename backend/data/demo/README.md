# CloudIntelliGuard Demo Dataset

## Overview

This directory contains a synthetic demo CloudTrail-style dataset for testing
and demonstration purposes.

## Files

| File | Description |
|------|-------------|
| `sample_cloudtrail.csv` | 100 cloud API events across 7 simulated users |
| `ground_truth_labels.json` | Human-assigned anomaly labels for evaluation |

## Dataset Design

### Users

| User | Behaviour | Anomalous? |
|------|-----------|-----------|
| U001 | Normal S3/EC2 read operations, business hours | No |
| U002 | Normal S3/Lambda data pipeline, business hours | No |
| U003 | Normal CloudFormation deployments, business hours | No |
| U004 | Normal DynamoDB read/write operations, business hours | No |
| U005 | Normal SNS/SQS messaging, business hours | No |
| U006 | Off-hours (02:00–04:30 UTC), IAM credential manipulation, Secrets Manager + KMS access, 33% failure rate | **Yes** |
| U007 | Off-hours (02:15–02:42 UTC), 40 requests in 31 minutes, 10+ service types, reconnaissance-like pattern | **Yes** |

### Coordinated Pattern

U006 and U007 have temporal overlap (02:15–04:00 UTC) and share service access
patterns (secretsmanager, kms, iam), making them a candidate for coordinated
detection testing.

## Important Notes

- **This is a synthetic dataset.** Events are hand-crafted to exercise specific
  anomaly detection scenarios. It does not represent real AWS activity.
- **Labels are observational.** Ground-truth labels describe observable behavioral
  patterns. No causal relationships or real-world attack attributions are claimed.
- **Anomaly types use "suspicious" only.** No invented attack category labels
  (e.g. "exfiltration", "privilege escalation") are used.

## Usage

Upload via the API:
```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@data/demo/sample_cloudtrail.csv"
```

Or enable `DEMO_MODE=true` in `.env` for automatic loading.
