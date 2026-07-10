#!/usr/bin/env python3
"""Push all files to GitHub repo via Git Data API (batch mode)."""
import json, os, base64, subprocess

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    TOKEN = "ghp_...s0V2PkCF5"
OWNER = "1yuanjichang"
REPO = "1yuanjichang.github.io"
BASE_DIR = "/c/Users/admin/1yuanjichang.github.io"

def gh_api(method, endpoint, data=None):
    url = f"https://api.github.com{endpoint}"
    cmd = ["curl", "-s", url, "-H", f"Authorization: token {TOKEN}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    result = json.loads(r.stdout)
    if "message" in result and "status" in result and str(result.get("status","0")).startswith("4"):
        print(f"  API Error ({endpoint}): {result['message']}")
    return result

print("Getting latest commit...")
ref = gh_api("GET", f"/repos/{OWNER}/{REPO}/git/refs/heads/main")
latest_sha = ref["object"]["sha"]
print(f"  Latest commit: {latest_sha}")

skip_dirs = {"node_modules", ".git", "vendor", ".bundle", "_site"}
blob_entries = []
for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        if f.endswith(".lock") or f == "push_to_github.py": continue
        rel_path = os.path.relpath(os.path.join(root, f), BASE_DIR).replace("\\", "/")
        if rel_path.startswith("./"): rel_path = rel_path[2:]
        full_path = os.path.join(root, f)
        try:
            with open(full_path, "rb") as fh:
                content = fh.read()
            b64 = base64.b64encode(content).decode()
            blob = gh_api("POST", f"/repos/{OWNER}/{REPO}/git/blobs",
                           {"content": b64, "encoding": "base64"})
            if "sha" in blob:
                blob_entries.append({"path": rel_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
                print(f"  Blob OK: {rel_path}")
            else:
                print(f"  FAILED: {rel_path} - {json.dumps(blob)[:200]}")
        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")

print(f"\nCreated {len(blob_entries)} blobs")
print("Creating tree...")
tree_data = gh_api("POST", f"/repos/{OWNER}/{REPO}/git/trees",
                   {"base_tree": latest_sha, "tree": blob_entries})
if "sha" not in tree_data:
    print(f"Tree creation failed: {tree_data}")
    exit(1)
tree_sha = tree_data["sha"]
print(f"  Tree SHA: {tree_sha}")

print("Creating commit...")
commit_data = gh_api("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
    "message": "Initial site deployment: 一元机场导航 Jekyll site\n\nFull Jekyll site with Tailwind CSS, dark mode, GSAP,\nAlpine.js, SEO (JSON-LD, sitemap, RSS), 30+ FAQ,\nsample posts, category pages.",
    "tree": tree_sha,
    "parents": [latest_sha]
})
if "sha" not in commit_data:
    print(f"Commit creation failed: {commit_data}")
    exit(1)
commit_sha = commit_data["sha"]
print(f"  Commit SHA: {commit_sha}")

print("Updating branch ref...")
result = gh_api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
                {"sha": commit_sha, "force": True})
if "ref" in result:
    print(f"  SUCCESS! Branch updated to {commit_sha}")
else:
    print(f"  Failed: {result}")
print("Done!")
