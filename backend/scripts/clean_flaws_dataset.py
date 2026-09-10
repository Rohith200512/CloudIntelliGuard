"""Data cleaning and ETL script for AWS CloudTrail / FlAWS dataset.
Cleans raw archive/nineteenFeaturesDf.csv into standardized canonical CloudIntelliGuard schema:
  - timestamp (ISO 8601 UTC)
  - user_id (Clean IAM user / role / identity string)
  - event_id (Unique UUID / event identifier)
  - action (Canonical API action name)
  - service (Normalized short service name, e.g. s3, iam, ec2, kms)
  - resource (ARN or constructed resource identifier)
  - source_ip (IPv4 / IPv6 address)
  - status (success / failure / AccessDenied)
"""
import os
import re
import pandas as pd
import numpy as np


def extract_clean_user(row):
    """Extract clean, meaningful IAM identity name from multiple CloudTrail fields."""
    # 1. Direct userName
    user_name = row.get('userIdentityuserName')
    if pd.notna(user_name) and str(user_name).strip() and str(user_name).lower() not in ('nan', 'unknown', 'none', ''):
        return str(user_name).strip()

    # 2. Extract from ARN (e.g. arn:aws:iam::811596193553:user/backup -> backup, arn:aws:iam::...:root -> root)
    arn = row.get('userIdentityarn')
    if pd.notna(arn) and str(arn).strip() and str(arn).lower() not in ('nan', 'none', ''):
        arn_str = str(arn).strip()
        if ':root' in arn_str:
            return 'root'
        if ':user/' in arn_str:
            return arn_str.split(':user/')[-1]
        if ':assumed-role/' in arn_str:
            parts = arn_str.split(':assumed-role/')[-1].split('/')
            role_name = parts[0]
            session = parts[1] if len(parts) > 1 else ''
            # Simplify session numbers
            if session and not session.isdigit():
                return f"{role_name}/{session}"
            return f"role/{role_name}"
        if ':role/' in arn_str:
            return f"role/{arn_str.split(':role/')[-1]}"
        # Generic ARN fallback
        return arn_str.split(':')[-1]

    # 3. Principal ID
    pid = row.get('userIdentityprincipalId')
    if pd.notna(pid) and str(pid).strip() and str(pid).lower() not in ('nan', 'none', ''):
        pid_str = str(pid).strip()
        if ':' in pid_str:
            return pid_str.split(':')[0]
        return pid_str

    # 4. Identity Type
    itype = row.get('userIdentitytype')
    if pd.notna(itype) and str(itype).strip() and str(itype).lower() not in ('nan', 'none', ''):
        return f"type/{str(itype).strip()}"

    return 'unknown_identity'


def clean_service_name(val):
    """Normalize AWS service domain to short service name (e.g. s3.amazonaws.com -> s3)."""
    if pd.isna(val) or not str(val).strip():
        return 'unknown'
    s = str(val).strip().lower()
    s = re.sub(r'\.amazonaws\.com(\.cn)?$', '', s)
    s = re.sub(r'\.aws\.amazon\.com$', '', s)
    # Common mappings
    mapping = {
        'monitoring': 'cloudwatch',
        'elasticloadbalancing': 'elb',
        'opsworks-cm': 'opsworks',
        'cognito-sync': 'cognito',
        'cognito-idp': 'cognito',
        'cognito-identity': 'cognito',
        'awslambda': 'lambda',
    }
    return mapping.get(s, s)


def clean_status(val):
    """Convert raw error codes to canonical status (success vs failure / error code)."""
    if pd.isna(val) or not str(val).strip() or str(val).lower() in ('nan', 'none', 'noerror', 'null', '0'):
        return 'success'
    err = str(val).strip()
    if 'AccessDenied' in err or 'Unauthorized' in err:
        return 'AccessDenied'
    return 'failure'


def clean_dataset(input_file: str, output_dir: str):
    """Read raw 19-features dataset, clean, sort, and save standardized outputs."""
    print(f"Reading and cleaning: {input_file} ...")
    os.makedirs(output_dir, exist_ok=True)

    cleaned_chunks = []
    chunk_size = 300000
    total_processed = 0

    for i, chunk in enumerate(pd.read_csv(input_file, chunksize=chunk_size, low_memory=False)):
        total_processed += len(chunk)
        print(f"  Processing chunk {i+1} ({total_processed:,} rows)...")

        # 1. Parse timestamps
        chunk['timestamp'] = pd.to_datetime(chunk['eventTime'], errors='coerce', utc=True)
        chunk = chunk[chunk['timestamp'].notna()].copy()

        # 2. Extract clean User ID
        chunk['user_id'] = chunk.apply(extract_clean_user, axis=1)

        # 3. Clean Event ID
        chunk['event_id'] = chunk['eventID'].fillna('').astype(str)

        # 4. Clean Action / eventName
        chunk['action'] = chunk['eventName'].fillna('UnknownAction').astype(str).str.strip()

        # 5. Clean Service / eventSource
        chunk['service'] = chunk['eventSource'].apply(clean_service_name)

        # 6. Clean Resource
        chunk['resource'] = 'arn:aws:' + chunk['service'] + ':::res/' + chunk['action']

        # 7. Clean Source IP
        chunk['source_ip'] = chunk['sourceIPAddress'].fillna('127.0.0.1').astype(str).str.strip()

        # 8. Clean Status
        chunk['status'] = chunk['errorCode'].apply(clean_status)

        canonical_chunk = chunk[[
            'timestamp', 'user_id', 'event_id', 'action', 'service', 'resource', 'source_ip', 'status'
        ]]
        cleaned_chunks.append(canonical_chunk)

    print("Concatenating and sorting cleaned dataset...")
    full_df = pd.concat(cleaned_chunks, ignore_index=True)

    # Deduplicate by event_id if present
    full_df = full_df.drop_duplicates(subset=['event_id']).reset_index(drop=True)

    # Sort chronologically
    full_df = full_df.sort_values(by='timestamp').reset_index(drop=True)
    full_df['timestamp'] = full_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"\nFinal Cleaned Rows: {len(full_df):,}")
    print(f"Unique Cleaned Users ({full_df['user_id'].nunique()}): {list(full_df['user_id'].unique()[:10])}")
    print(f"Unique Cleaned Services ({full_df['service'].nunique()}): {list(full_df['service'].unique()[:10])}")
    print(f"Status Distribution:\n{full_df['status'].value_counts()}")

    # Save 1: 10,000-event fast demo sample (rich distribution of all users)
    sample_10k = full_df.iloc[:10000]
    sample_10k_path = os.path.join(output_dir, 'flaws_cloudtrail_sample_10k.csv')
    sample_10k.to_csv(sample_10k_path, index=False)
    print(f"\nSaved 10k Sample Dataset: {sample_10k_path} ({os.path.getsize(sample_10k_path)/(1024*1024):.2f} MB)")

    # Save 2: 50,000-event benchmark sample
    sample_50k = full_df.iloc[:50000]
    sample_50k_path = os.path.join(output_dir, 'flaws_cloudtrail_sample_50k.csv')
    sample_50k.to_csv(sample_50k_path, index=False)
    print(f"Saved 50k Benchmark Dataset: {sample_50k_path} ({os.path.getsize(sample_50k_path)/(1024*1024):.2f} MB)")

    # Save 3: Full Cleaned Dataset
    full_path = os.path.join(output_dir, 'flaws_cloudtrail_cleaned_full.csv')
    full_df.to_csv(full_path, index=False)
    print(f"Saved Full Cleaned Dataset: {full_path} ({os.path.getsize(full_path)/(1024*1024):.2f} MB)")


if __name__ == '__main__':
    raw_path = 'C:/Users/hp/.gemini/antigravity/scratch/CloudIntelliGuard/archive/nineteenFeaturesDf.csv'
    out_dir = 'C:/Users/hp/.gemini/antigravity/scratch/CloudIntelliGuard/backend/data/processed'
    clean_dataset(raw_path, out_dir)
