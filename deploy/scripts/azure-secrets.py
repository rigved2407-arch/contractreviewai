#!/usr/bin/env python3
"""
Sync secrets from Azure Key Vault → local .secrets/ directory.

Usage:
    python deploy/scripts/azure-secrets.py \
        --vault-url https://contract-review-ai-kv.vault.azure.net \
        --secret-name production-secrets

Requires: azure-identity, azure-keyvault-secrets
    pip install azure-identity azure-keyvault-secrets

The secret must be stored as a single secret with key=value lines (like a .env file)
or as a JSON blob. Each key-value pair becomes a file in .secrets/.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch secrets from Azure Key Vault")
    parser.add_argument("--vault-url", required=True, help="Key Vault URL (e.g. https://xxx.vault.azure.net)")
    parser.add_argument("--secret-name", required=True, help="Name of the secret in the vault")
    parser.add_argument("--secrets-dir", default=".secrets", help="Output directory")
    args = parser.parse_args()

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError:
        print(
            "ERROR: azure-identity and azure-keyvault-secrets are required.\n"
            "  Install with: pip install azure-identity azure-keyvault-secrets",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Authenticating to Azure Key Vault at {args.vault_url}...")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=args.vault_url, credential=credential)

    print(f"Fetching secret '{args.secret_name}'...")
    secret_bundle = client.get_secret(args.secret_name)
    secret_value = secret_bundle.value

    if not secret_value:
        print("ERROR: Secret value is empty", file=sys.stderr)
        sys.exit(1)

    # Try JSON first, then key=value lines
    try:
        secrets = json.loads(secret_value)
    except json.JSONDecodeError:
        secrets = {}
        for line in secret_value.strip().splitlines():
            line = line.strip()
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
