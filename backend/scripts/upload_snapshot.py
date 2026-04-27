"""
Upload local Qdrant snapshot to a remote Qdrant instance (e.g. Qdrant Cloud).

Usage:
    python scripts/upload_snapshot.py \
        --snapshot /tmp/npa.snapshot \
        --url https://YOUR-CLUSTER.qdrant.io \
        --api-key YOUR-API-KEY \
        --collection npa
"""

import argparse
import sys
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--url", required=True, help="e.g. https://xyz.qdrant.io")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--collection", default="npa")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    headers = {"api-key": args.api_key}

    # 1. Delete existing collection if it exists
    resp = requests.delete(f"{base}/collections/{args.collection}", headers=headers)
    print(f"Delete collection: {resp.status_code}")

    # 2. Upload snapshot
    print(f"Uploading snapshot {args.snapshot} ({sys.getsizeof(open(args.snapshot,'rb').read())} bytes)...")
    with open(args.snapshot, "rb") as f:
        resp = requests.post(
            f"{base}/collections/{args.collection}/snapshots/upload",
            headers=headers,
            files={"snapshot": (args.snapshot.split("/")[-1], f, "application/octet-stream")},
            params={"priority": "snapshot"},
            timeout=300,
        )
    print(f"Upload: {resp.status_code} {resp.text[:200]}")
    if resp.status_code == 200:
        print("✅ Snapshot uploaded successfully!")
    else:
        print("❌ Upload failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
