"""Helpers for the manual GHCR / SingularityCE release workflow.

Only the workflow's publish job calls publish(). Tests use injected API/CLI fakes.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
SOURCE_NAMES = ("rest_workspace", "rest", "rest_tensors", "rest_libcint", "rest_regression")


def run(*command, **kwargs):
    return subprocess.check_output(command, text=True, timeout=120, **kwargs).strip()


class GitHub:
    def __init__(self):
        self.token = os.environ["GH_TOKEN"]

    def request(self, path, method="GET", data=None, missing_ok=False):
        if not path.startswith("/"):
            raise ValueError("GitHub API paths must be relative")
        request = Request("https://api.github.com" + path,
                          data=None if data is None else json.dumps(data).encode(), method=method,
                          headers={"Authorization": "Bearer " + self.token,
                                   "Accept": "application/vnd.github+json",
                                   "Content-Type": "application/json", "User-Agent": "rest-manual-release"})
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise RuntimeError(f"GitHub API {method} {path}: HTTP {error.code}") from None

    def pages(self, path, missing_ok=False):
        separator = "&" if "?" in path else "?"
        page = 1
        while True:
            values = self.request(f"{path}{separator}per_page=100&page={page}", missing_ok=missing_ok)
            if values is None:
                return
            yield from values
            if len(values) < 100:
                return
            page += 1


def release_date(started_at):
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    if started.tzinfo is None:
        raise ValueError("Workflow start time must include a timezone")
    return started.astimezone(ZoneInfo("Asia/Shanghai"))


def next_version(day, existing):
    """Use a shared daily sequence across both packages and Release/Git tags."""
    prefix = day.strftime("%y%m%d")
    pattern = re.compile(re.escape(prefix) + r"(?:-([2-9]|[1-9][0-9]+))?\Z")
    used = [int(match[1] or 1) for value in existing if (match := pattern.fullmatch(value))]
    number = max(used, default=0) + 1
    return prefix if number == 1 else f"{prefix}-{number}"


def image_repository(reference):
    if not re.fullmatch(r"[a-z0-9][a-z0-9._:/@-]*", reference):
        raise ValueError(f"Invalid container reference: {reference!r}")
    repository = reference.split("@", 1)[0]
    if ":" in repository.rsplit("/", 1)[-1]:
        repository = repository.rsplit(":", 1)[0]
    return repository


def image_digest(reference):
    image_repository(reference)
    manifest = json.loads(run("docker", "buildx", "imagetools", "inspect", reference,
                              "--format", "{{json .Manifest}}"))
    digest = manifest["digest"]
    if not DIGEST.fullmatch(digest):
        raise ValueError("Registry returned an invalid digest")
    if "@" in reference and reference.split("@", 1)[1] != digest:
        raise ValueError("Resolved digest differs from the requested digest")
    return digest


def pinned_image(reference):
    return image_repository(reference) + "@" + image_digest(reference)


def source_revision(name):
    result = run("git", "ls-remote", "--exit-code", f"https://gitee.com/restgroup/{name}.git", "HEAD")
    revision = result.split()[0]
    if not REVISION.fullmatch(revision):
        raise ValueError(f"Invalid Git revision for {name}")
    return name, revision


def output_dir():
    directory = Path(os.environ["CI_OUTPUT_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def outputs(values):
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as file:
        for name, value in values.items():
            if "\n" in str(value) or "\r" in str(value):
                raise ValueError("Multiline job output is not allowed")
            file.write(f"{name}={value}\n")


def load_plan():
    return json.loads((output_dir() / "plan.json").read_text())


def prepare():
    api = GitHub()
    repository = os.environ["GITHUB_REPOSITORY"]
    repo = api.request(f"/repos/{repository}")
    if os.environ["GITHUB_REF"] != "refs/heads/" + repo["default_branch"]:
        raise ValueError("Run the publishing workflow from the repository's default branch")
    target = os.environ["BUILD_TARGET"]
    if target not in {"dependencies", "rest", "all"}:
        raise ValueError("Unknown build target")
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    workflow = api.request(f"/repos/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}/attempts/{attempt}")
    day = release_date(workflow["run_started_at"])
    existing = {tag["name"] for tag in api.pages(f"/repos/{repository}/tags")}
    existing.update(release["tag_name"] for release in api.pages(f"/repos/{repository}/releases"))
    owner = repo["owner"]["login"]
    owner_kind = "orgs" if repo["owner"]["type"] == "Organization" else "users"
    for package in ("rest_dependencies", "rest"):
        path = f"/{owner_kind}/{quote(owner, safe='')}/packages/container/{package}/versions"
        for version in api.pages(path, missing_ok=True):
            existing.update(version.get("metadata", {}).get("container", {}).get("tags", []))
    version = next_version(day, existing)
    suffix = version[len(day.strftime("%y%m%d")):]
    namespace = "ghcr.io/" + owner.lower()
    sources = {}
    if target != "dependencies":
        with ThreadPoolExecutor(max_workers=5) as pool:
            sources = dict(pool.map(source_revision, SOURCE_NAMES))
    plan = {
        "repository": repository, "workflow_commit": os.environ["GITHUB_SHA"],
        "run_id": os.environ["GITHUB_RUN_ID"], "run_attempt": attempt,
        "started_at": workflow["run_started_at"], "timezone": "Asia/Shanghai",
        "version": version, "release_name": "Release " + day.strftime("%Y.%m.%d") + suffix,
        "sif_name": "rest_" + version + ".sif", "target": target, "sources": sources,
        "dependencies_tag": namespace + "/rest_dependencies:" + version,
        "rest_tag": namespace + "/rest:" + version,
        "rust_image": pinned_image("rust:slim-trixie") if target != "rest" else "",
        "runtime_image": pinned_image("debian:trixie-slim") if target != "dependencies" else "",
        "dependencies_image": pinned_image(os.environ["DEPENDENCIES_IMAGE"]) if target == "rest" else "",
    }
    write_json(output_dir() / "plan.json", plan)
    outputs({**{key: plan[key] for key in ("version", "release_name", "sif_name", "dependencies_tag",
                                         "rest_tag", "rust_image", "runtime_image", "dependencies_image")},
             **{name + "_revision": sources.get(name, "") for name in SOURCE_NAMES}})
    print(f"{plan['release_name']} ({target}); all dates use Asia/Shanghai")


def host_tools():
    return {name: run(*command) for name, command in {
        "docker": ("docker", "version"), "buildx": ("docker", "buildx", "version"),
        "github_cli": ("gh", "--version"), "kernel": ("uname", "-sr"),
    }.items()}


def image_info(kind):
    plan = load_plan()
    reference = plan["dependencies_tag" if kind == "dependencies" else "rest_tag"]
    digest = os.environ["IMAGE_DIGEST"]
    if not DIGEST.fullmatch(digest) or image_digest(reference) != digest:
        raise ValueError("Published image digest does not match the build output")
    reference = image_repository(reference) + "@" + digest
    subprocess.run(["docker", "pull", "--platform", "linux/amd64", reference], check=True)
    metadata_path = "/opt/" + ("dependencies" if kind == "dependencies" else "rest") + "-build-info.json"
    metadata = json.loads(run("docker", "run", "--rm", "--network=none", "--entrypoint", "python3", reference,
                              "-c", "from pathlib import Path; print(Path(" + repr(metadata_path) + ").read_text())"))
    if kind == "rest" and metadata["sources"] != plan["sources"]:
        raise ValueError("Built source revisions differ from the prepared source lock")
    info = {"reference": reference, "tag": plan[kind + "_tag"], "digest": digest,
            "container": metadata, "host_tools": host_tools(),
            "buildkit_nodes": json.loads(os.environ["BUILDKIT_NODES"]),
            "build_metadata": json.loads(os.environ["BUILD_METADATA"])}
    if kind == "rest":
        info["container"]["regression"] = {"root": "passed", "admin": "passed"}
        info["dependencies_image"] = os.environ["USED_DEPENDENCIES_IMAGE"]
        outputs({"digest": digest})
    else:
        outputs({"reference": reference, "digest": digest})
    write_json(output_dir() / (kind + "-info.json"), info)


def check_tag(kind):
    """A failed-job rerun must never overwrite an image pushed by an earlier job."""
    plan = load_plan()
    api = GitHub()
    repo = api.request("/repos/" + plan["repository"])
    owner_kind = "orgs" if repo["owner"]["type"] == "Organization" else "users"
    package = "rest_dependencies" if kind == "dependencies" else "rest"
    path = f"/{owner_kind}/{quote(repo['owner']['login'], safe='')}/packages/container/{package}/versions"
    for value in api.pages(path, missing_ok=True):
        if plan["version"] in value.get("metadata", {}).get("container", {}).get("tags", []):
            raise ValueError("Version already exists; start a new Run workflow to allocate a new suffix")


def smoke_sif(sif):
    plan = load_plan()
    work = output_dir() / "sif-smoke"
    work.mkdir(exist_ok=True)
    work = work.resolve()
    sif = str(Path(sif).resolve())
    options = ["--cleanenv", "--containall", "--no-eval", "--bind", str(work) + ":/data", "--pwd", "/data"]
    subprocess.run(["singularity", "run", *options, sif, "--help"], check=True, timeout=90)
    probe = '''import ctypes, json, os
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
import geometric, ase
assert os.geteuid() != 0
np.testing.assert_allclose(eigh(np.array([[2.,1.],[1.,2.]]), eigvals_only=True), [1.,3.])
for library in Path('/opt/dependency/lib').glob('*.so*'):
    if library.is_file() and not library.is_symlink(): ctypes.CDLL(str(library))
print('SIF Python, linear algebra and native-library checks passed')
'''
    subprocess.run(["singularity", "exec", *options, sif, "python3", "-c", probe], check=True, timeout=90)
    fixture = Path(__file__).with_name("sif-smoke.in")
    (work / "ctrl.in").write_bytes(fixture.read_bytes())
    with (work / "rest.log").open("w") as log:
        result = subprocess.run(["singularity", "run", *options, sif, "-i", "ctrl.in"],
                                stdout=log, stderr=subprocess.STDOUT, timeout=300)
    text = (work / "rest.log").read_text()
    print(text)
    result.check_returncode()
    energies = re.findall(r"The SCF energy\s*:\s*([+-]?[0-9]+\.[0-9]+)", text)
    if not energies or abs(float(energies[-1]) - (-75.9612828916)) > 1e-6:
        raise ValueError("SIF H2O/HF energy differs from the reference by more than 1e-6 Eh")
    path = Path(sif)
    if path.name != plan["sif_name"] or path.stat().st_size >= 2 * 1024**3:
        raise ValueError("Unexpected SIF name or SIF exceeds the GitHub Release asset limit")
    with path.open("rb") as file:
        checksum = hashlib.file_digest(file, "sha256").hexdigest()
    (output_dir() / "SHA256SUMS").write_text(checksum + "  " + path.name + "\n")
    write_json(output_dir() / "sif-info.json", {
        "file": path.name, "sha256": checksum, "size": path.stat().st_size,
        "singularity": run("singularity", "version"), "host_tools": host_tools(),
        "tests": {"entrypoint": "passed", "python_native_libraries": "passed", "h2o_hf": "passed"},
        "scf_energy": float(energies[-1]),
    })


def promote(reference):
    repository = image_repository(reference)
    digest = reference.split("@", 1)[1]
    if not DIGEST.fullmatch(digest):
        raise ValueError("Promotion requires a digest-pinned image")
    subprocess.run(["docker", "buildx", "imagetools", "create", "--prefer-index=false",
                    "--tag", repository + ":latest", reference], check=True)
    if image_digest(repository + ":latest") != digest:
        raise ValueError("latest does not match the validated version digest")


def publish():
    plan = load_plan()
    directory = output_dir()
    built = {}
    for kind in ("dependencies", "rest"):
        path = directory / (kind + "-info.json")
        if path.exists():
            built[kind] = json.loads(path.read_text())
    expected = {"dependencies", "rest"} if plan["target"] == "all" else {plan["target"]}
    if set(built) != expected:
        raise ValueError("Missing or unexpected image validation records")
    if "rest" in built:
        if built["rest"]["container"]["regression"] != {"root": "passed", "admin": "passed"}:
            raise ValueError("Both regression runs must pass before publishing")
        sif = json.loads((directory / "sif-info.json").read_text())
        if set(sif["tests"].values()) != {"passed"}:
            raise ValueError("SIF checks did not all pass")
        asset = directory / plan["sif_name"]
        with asset.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != sif["sha256"]:
                raise ValueError("SIF changed after verification")
        write_json(directory / "build-info.json", {"build": plan, "images": built, "sif": sif})
        api = GitHub()
        repo = plan["repository"]
        release = api.request(f"/repos/{repo}/releases/tags/{plan['version']}", missing_ok=True)
        if release is None:
            release = api.request(f"/repos/{repo}/releases", method="POST", data={
                "tag_name": plan["version"], "target_commitish": plan["workflow_commit"],
                "name": plan["release_name"], "draft": True, "make_latest": "false",
                "body": "REST image: `" + built["rest"]["reference"] + "`\n\n"
                        "Dates use Asia/Shanghai. Source revisions and tools are in build-info.json.",
            })
        if not release["draft"]:
            raise ValueError("Refusing to overwrite an already published Release")
        subprocess.run(["gh", "release", "upload", plan["version"], str(asset),
                        str(directory / "SHA256SUMS"), str(directory / "build-info.json"),
                        "--repo", repo, "--clobber"], check=True)
        api.request(f"/repos/{repo}/releases/{release['id']}", method="PATCH",
                    data={"draft": False, "make_latest": "true"})
    # No latest tag is touched until every requested image / SIF has passed.
    # These registry/API operations are not transactional: failures remain visible
    # and a subsequent manual build receives a fresh version rather than overwriting.
    for kind in ("dependencies", "rest"):
        if kind in built:
            promote(built[kind]["reference"])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as file:
            file.write("## " + plan["release_name"] + "\n\n")
            for info in built.values():
                file.write("- `" + info["tag"] + "` → `" + info["digest"] + "`\n")
            if "rest" in built:
                file.write(f"- [SIF Release](https://github.com/{plan['repository']}/releases/tag/{plan['version']})\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check-tag", "image-info", "smoke-sif", "publish"))
    parser.add_argument("--kind", choices=("dependencies", "rest"))
    parser.add_argument("--sif")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command in {"image-info", "check-tag"}:
        if not args.kind:
            parser.error(args.command + " requires --kind")
        (image_info if args.command == "image-info" else check_tag)(args.kind)
    elif args.command == "smoke-sif":
        if not args.sif:
            parser.error("smoke-sif requires --sif")
        smoke_sif(args.sif)
    else:
        publish()


if __name__ == "__main__":
    main()
