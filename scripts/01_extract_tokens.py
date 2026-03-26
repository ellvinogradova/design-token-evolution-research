#!/usr/bin/env python3
"""Day 2: shallow + sparse clone each locked system at its before/after tag,
materializing only the token source paths confirmed during the Day 1
pre-flight check. Reads data/preflight/*.json as the single source of truth
for repo URLs, tags, and paths -- nothing here is hardcoded separately from
what was actually verified.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_DIR = ROOT / "data" / "preflight"
REPOS_DIR = ROOT / "data" / "repos"

# preflight files that represent the *locked* sample (excludes the
# preserved-but-unused Atlassian investigation).
LOCKED_FILES = [
    "ant-design.json",
    "fluent-ui.json",
    "carbon.json",
    "material-mui.json",
    "shopify-polaris.json",
]

SLUG_OVERRIDE = {
    "Ant Design": "ant-design",
    "Fluent UI": "fluent-ui",
    "Carbon Design System": "carbon",
    "Material Design / MUI": "mui",
}


def slug_for(system_name: str) -> str:
    if system_name in SLUG_OVERRIDE:
        return SLUG_OVERRIDE[system_name]
    if system_name.startswith("Shopify Polaris"):
        return "polaris"
    return system_name.lower().replace(" ", "-")


def run(cmd, cwd=None, check=True):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result


def sparse_clone(repo_url: str, tag: str, paths: list[str], dest: Path):
    if dest.exists():
        print(f"  -> {dest} already exists, skipping")
        return
    dest.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], cwd=dest)
    run(["git", "remote", "add", "origin", repo_url], cwd=dest)
    run(["git", "config", "core.sparseCheckout", "true"], cwd=dest)

    sparse_file = dest / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    with open(sparse_file, "w") as f:
        for p in paths:
            f.write(p.rstrip("/") + "\n")
            f.write(p.rstrip("/") + "/**\n")

    run(["git", "fetch", "--depth", "1", "--filter=blob:none", "origin", tag], cwd=dest)
    run(["git", "checkout", "FETCH_HEAD"], cwd=dest)


def main():
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for fname in LOCKED_FILES:
        path = PREFLIGHT_DIR / fname
        data = json.loads(path.read_text())
        system = data["system"]
        slug = slug_for(system)
        repo_url = data["repo_url"]
        print(f"\n=== {system} ({slug}) ===")

        for phase in ("before", "after"):
            tag = data[f"{phase}_tag"]
            paths = data[f"{phase}_token_paths"]
            dest = REPOS_DIR / slug / phase
            print(f" [{phase}] tag={tag} -> {dest}")
            sparse_clone(repo_url, tag, paths, dest)
            manifest.append(
                {
                    "system": system,
                    "slug": slug,
                    "phase": phase,
                    "tag": tag,
                    "paths": paths,
                    "dest": str(dest.relative_to(ROOT)),
                }
            )

    manifest_path = ROOT / "data" / "extraction-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nWrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
