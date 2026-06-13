#!/usr/bin/env python3
"""
Sync secrets from AWS Secrets Manager → local .secrets/ directory.

Usage:
    python deploy/scripts/aws-secrets.py \
        --secret-id contract-review-ai/production \
        --region ap-south-1

Requires: boto3, awscli (IAM role with secretsmanager:GetSecretValue)

Secrets are written to .secrets/ as individual files, ready for
docker-compose -f docker-compose.yml -f deploy/docker-compose.secrets.yml
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch secrets from AWS Secrets Manager")
    parser.add_argument("--secret-id", required=True, help="Name or ARN of the secret")
    parser.add_argument("--region", default="ap-south-1", help="AWS region")
    parser.add_argument("--profile", default=None, help="AWS profile name")
    parser.add_argument("--secrets-dir", default=".secrets", help="Output directory")
    args = parser.parse_args()

    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is required. Install with: pip install boto3", file=sys.stderr)
        sys.exit(1)

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client = session.client("secretsmanager")

    print(f"Fetching secret '{args.secret_id}' from region {args.region}...")
    response = client.get_secret_value(SecretId=args.secret_id)

    secret_string = response.get("SecretString")
    if not secret_string:
        print("ERROR: Secret has no SecretString", file=sys.stderr)
        sys.exit(1)

    try:
        secrets = json.loads(secret_string)
    except json.JSONDecodeError:
        # Try parsing as key=value lines
        secrets = {}
        for line in secret_string.strip().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip()

    secrets_dir = Path(args.secrets_dir)
    secrets_dir.mkdir(parents=True, exist_ok=True)

    for key, value in secrets.items():
        filepath = secrets_dir / key
        filepath.write_text(value)
        print(f"  Wrote {filepath}")

    print(f"Done — {len(secrets)} secrets synced to {secrets_dir}/")


if __name__ == "__main__":
    main()
