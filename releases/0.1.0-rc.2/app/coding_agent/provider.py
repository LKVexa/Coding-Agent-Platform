"""Pinned, proposal-only Codex CLI adapter using the existing ChatGPT login.

The CLI remains a trusted local credential holder. Tool registration is suppressed
by a pinned catalog and explicit configuration; this is not OS process isolation.
The CLI also retains its built-in instructions and any global CODEX_HOME/AGENTS
guidance. Ignore-user-config does not suppress that global guidance. Canary tests
confirm project instructions and config are excluded; inherited global guidance
cannot grant absent tools and is recorded as a remaining trust assumption.
Only bounded caller-supplied public context should be supplied in ``prompt``.
The caller must independently authorize and evaluate any returned change.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import uuid

CLI_VERSION = "codex-cli 0.166.0-alpha.5.1"
EXPECTED_MODEL = "gpt-6.1-sol"
CLI_SHA256 = "3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16"
CATALOG_SHA256 = "8c88ee259973cae57cfd64953538d56c1d6b47ad22b8a7c4796bd1c69303dcda"
CATALOG = Path(__file__).parent / "resources" / "no-tools-models.json"
INSTRUCTION_POLICY = {
    "project_instructions": "disabled; canary verified",
    "user_config": "ignored; canary verified",
    "skill_catalog": "disabled; no resource entries in canary capture",
    "global_guidance": "CLI may inherit CODEX_HOME/AGENTS.override.md or AGENTS.md",
    "builtin_instructions": "pinned model catalog instructions retained",
    "pure_prompt_isolation": False,
    "global_guidance_contents_recorded": False,
}
INHERITED_GUIDANCE = "global CODEX_HOME/AGENTS.md may be included; project docs/config disabled"
MAX_PROMPT_BYTES = 65536
MAX_SCHEMA_BYTES = 32768
MAX_RESPONSE_BYTES = 131072
MAX_DIAGNOSTIC_BYTES = 262144
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "view_image", "sleep_tool", "apps", "plugins",
    "plugin_discovery_prefetch", "plugin_sharing", "remote_plugin", "browser_use",
    "browser_use_external", "browser_annotation_api", "browser_use_full_cdp_access",
    "computer_use", "in_app_browser", "in_app_chat", "in_app_local_automation",
    "image_generation", "multi_agent", "multi_agent_v2", "multi_agent_v2_dynamic_tools",
    "code_mode_host", "code_mode", "code_mode_only", "incremental_tools", "hooks",
    "skill_search", "skill_mcp_dependency_install", "tool_suggest",
    "workspace_dependencies", "memories", "goals", "daemon_auto_start", "shell_snapshot",
)


class ProviderError(RuntimeError):
    """Safe diagnostic; never contains raw CLI output or environment values."""

    def __init__(self, code: str, message: str, evidence: dict | None = None):
        super().__init__(message)
        self.code = code
        self.evidence = evidence or {}


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _resolve_cli() -> str:
    """Find the approved native binary without executing unverified candidates.

    Explorer and standalone terminals do not inherit the desktop app's PATH.
    An explicit override is authoritative; automatic discovery still accepts
    only the exact existing release hash, never a version label alone.
    """
    override = os.environ.get("CODING_AGENT_CODEX")
    candidates: list[Path] = []
    if override is not None:
        path = Path(override)
        if not override or not path.is_absolute() or path.suffix.lower() != ".exe":
            raise ProviderError("invalid_cli_path", "CODING_AGENT_CODEX must be the full path to the verified codex.exe.")
        candidates.append(path)
    else:
        found = shutil.which("codex")
        if found:
            path = Path(found).absolute()
            # A qualified PATH executable does not depend on fallback discovery.
            if path.is_file() and path.suffix.lower() == ".exe" and not _linked_path(path):
                if _digest(path) == CLI_SHA256:
                    return str(path)
            candidates.append(path)
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        managed = local / "OpenAI/Codex/bin"
        if managed.is_dir() and not _linked_path(managed):
            children = list(itertools.islice(managed.iterdir(), 129))
            if len(children) > 128:
                raise ProviderError("cli_discovery_limit", "Set CODING_AGENT_CODEX to the full path of the verified codex.exe.")
            for child in sorted(children, key=lambda item: item.name):
                if child.is_dir() and not _linked_path(child):
                    candidates.append(child / "codex.exe")
    present = False
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            continue
        present = True
        if path.suffix.lower() != ".exe" or _linked_path(path):
            continue
        if _digest(path) == CLI_SHA256:
            return str(path.absolute())
    if present:
        raise ProviderError("cli_mismatch", "No discovered Codex CLI matches the verified release. Re-verification is required for a different binary.")
    raise ProviderError("cli_not_found", "The verified Codex CLI was not found. Install or open Codex, or set CODING_AGENT_CODEX to its full codex.exe path.")


def _linked_path(path: Path) -> bool:
    return any(item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction())
               for item in (path, *path.parents))


def _environment() -> dict[str, str]:
    # Keep Windows/keyring login discovery; discard inherited agent tool pipes,
    # provider API keys, endpoint overrides, and other ambient application state.
    allowed = {"systemroot", "windir", "systemdrive", "comspec", "path", "pathext",
               "userprofile", "homedrive", "homepath", "appdata", "localappdata",
               "programdata", "programfiles", "programfiles(x86)", "temp", "tmp",
               "username", "userdomain", "codex_home"}
    return {key: value for key, value in os.environ.items() if key.lower() in allowed}


def _guidance_presence() -> dict:
    """Presence only: never open, fingerprint, or copy global instruction files."""
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    for name in ("AGENTS.override.md", "AGENTS.md"):
        if (codex_home / name).is_file():
            return {"present": True, "filename": name, "contents_read": False}
    return {"present": False, "filename": None, "contents_read": False}


def _capture(argv: list[str], *, cwd: Path, env: dict[str, str],
             stdin: bytes = b"", timeout: float, response: Path | None = None,
             cancel_path: Path | None = None
             ) -> tuple[int, str, str]:
    """Drain both pipes with a combined cap, and kill on timeout or overrun."""
    try:
        process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise ProviderError("cli_start_failed", "The pinned Codex CLI could not start.") from exc
    chunks: list[list[bytes]] = [[], []]
    lock = threading.Lock()
    total = [0]
    exceeded = threading.Event()

    def drain(pipe, bucket: int) -> None:
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    break
                with lock:
                    total[0] += len(chunk)
                    if total[0] > MAX_DIAGNOSTIC_BYTES:
                        exceeded.set()
                    else:
                        chunks[bucket].append(chunk)
        finally:
            pipe.close()

    readers = [threading.Thread(target=drain, args=(process.stdout, 0), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, 1), daemon=True)]
    for reader in readers:
        reader.start()
    def send_input() -> None:
        try:
            process.stdin.write(stdin)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
    writer = threading.Thread(target=send_input, daemon=True)
    writer.start()
    deadline = time.monotonic() + timeout
    failure = None
    try:
        while process.poll() is None:
            if cancel_path is not None and cancel_path.exists():
                failure = ProviderError("CANCELLED", "The provider call was cancelled.")
                break
            if exceeded.is_set() or (response is not None and response.exists()
                                      and response.stat().st_size > MAX_RESPONSE_BYTES):
                failure = ProviderError("output_limit", "The provider exceeded its output limit.")
                break
            if time.monotonic() >= deadline:
                failure = ProviderError("timeout", "The provider exceeded its time limit.")
                break
            time.sleep(0.05)
    finally:
        if process.poll() is None:
            if os.name == "nt":
                # This PID belongs to the child we just created. /T includes its
                # local helper children so a timed-out call cannot keep running.
                taskkill = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "taskkill.exe"
                try:
                    subprocess.run([str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                                   shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                except (OSError, subprocess.TimeoutExpired):
                    pass
            if process.poll() is None:
                process.kill()
        process.wait(timeout=5)
        writer.join(timeout=2)
        for reader in readers:
            reader.join(timeout=2)
    if failure:
        raise failure
    if exceeded.is_set():
        raise ProviderError("output_limit", "The provider exceeded its output limit.")
    return process.returncode, *(b"".join(bucket).decode("utf-8", errors="replace") for bucket in chunks)


def _verify_catalog() -> set[str]:
    if not CATALOG.is_file() or CATALOG.is_symlink() or _digest(CATALOG) != CATALOG_SHA256:
        raise ProviderError("catalog_mismatch", "The verified proposal-only model catalog has changed.")
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    models = data["models"]
    for model in models:
        expected = {"shell_type": "disabled", "apply_patch_tool_type": None,
                    "experimental_supported_tools": [], "tool_mode": "direct",
                    "multi_agent_version": "disabled", "supports_search_tool": False}
        if any(model.get(key) != value for key, value in expected.items()):
            raise ProviderError("catalog_unsafe", "The catalog enables an unexpected tool surface.")
    return {model["slug"] for model in models}


def provider_info() -> dict:
    """Read-only identity/authentication preflight; performs no inference call."""
    try:
        known_models = _verify_catalog()
        executable = _resolve_cli()
        env = _environment()
        code, stdout, _ = _capture([executable, "--version"], cwd=CATALOG.parent, env=env, timeout=10)
        if code != 0 or stdout.strip() != CLI_VERSION:
            raise ProviderError("cli_mismatch", "The Codex CLI version differs from the verified release.")
        code, stdout, stderr = _capture([executable, "login", "status"], cwd=CATALOG.parent, env=env, timeout=10)
        if code != 0 or "Logged in using ChatGPT" not in stdout + stderr:
            raise ProviderError("chatgpt_login_required", "The verified Codex CLI requires an existing ChatGPT login.")
        return {"name": "codex-chatgpt", "executable": executable, "cli_version": CLI_VERSION,
                "cli_sha256": CLI_SHA256, "catalog_sha256": CATALOG_SHA256,
                "authentication": "existing-chatgpt-login", "allowed_models": sorted(known_models),
                "catalog_default_candidate": EXPECTED_MODEL, "expected_resolved_model": EXPECTED_MODEL,
                "default_overridden": False, "model_identity_source": "CLI header on each call",
                "backend_identity_independently_verified": False,
                "inherited_guidance": INHERITED_GUIDANCE, "global_guidance": _guidance_presence(),
                "tool_policy": "pinned-catalog-no-tools", "cost": None,
                "instruction_policy": dict(INSTRUCTION_POLICY),
                "trust_boundary": "trusted-local-cli; tool suppression is not OS file isolation"}
    except OSError as exc:
        raise ProviderError("provider_io_failed", "The provider preflight could not read its local verified files.") from exc


def _argv(executable: str, cwd: Path, schema: Path, response: Path) -> list[str]:
    argv = [executable, "--no-daemon", "-a", "never", "exec", "--ignore-user-config",
            "--ignore-rules", "--ephemeral", "--skip-git-repo-check", "-C", str(cwd),
            "--sandbox", "read-only", "--color", "never", "--strict-config",
            "--enable", "skip_host_skill_discovery",
            "--output-schema", str(schema), "--output-last-message", str(response)]
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    overrides = {
        "model_catalog_json": CATALOG.resolve().as_posix(),
        "model_provider": "openai", "web_search": "disabled", "project_doc_max_bytes": 0,
        "skills.include_instructions": False, "tools.update_plan.enabled": False,
        "tools.experimental_request_user_input.enabled": False, "agents.enabled": False,
        "skills.bundled.enabled": False, "cloud.skills.enabled": False,
    }
    for key, value in overrides.items():
        argv.extend(["-c", key + "=" + json.dumps(value)])
    return argv + ["-"]


def _check_schema(schema: dict, depth: int = 0) -> None:
    allowed = {"$schema", "title", "description", "type", "properties", "required",
               "additionalProperties", "items", "enum", "const", "minLength", "maxLength",
               "minimum", "maximum", "minItems", "maxItems", "anyOf", "oneOf"}
    if depth > 20 or not isinstance(schema, dict) or set(schema) - allowed:
        raise ValueError("unsupported schema")
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        raise ValueError("invalid schema properties")
    for child in props.values():
        _check_schema(child, depth + 1)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            if not isinstance(schema[key], list) or not schema[key]:
                raise ValueError("invalid schema union")
            for child in schema[key]:
                _check_schema(child, depth + 1)
    for key in ("items", "additionalProperties"):
        if key in schema and isinstance(schema[key], dict):
            _check_schema(schema[key], depth + 1)


def _validate(value, schema: dict, depth: int = 0) -> None:
    """Validate the deliberately small proposal-schema subset without dependencies."""
    if depth > 20:
        raise ValueError("schema depth")
    allowed = {"$schema", "title", "description", "type", "properties", "required",
               "additionalProperties", "items", "enum", "const", "minLength", "maxLength",
               "minimum", "maximum", "minItems", "maxItems", "anyOf", "oneOf"}
    if not isinstance(schema, dict) or set(schema) - allowed:
        raise ValueError("unsupported schema")
    types = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int,
             "number": lambda v: type(v) in (int, float), "boolean": lambda v: type(v) is bool,
             "null": lambda v: v is None}
    kind = schema.get("type")
    if kind is not None:
        choices = kind if isinstance(kind, list) else [kind]
        if not any(name in types and types[name](value) for name in choices):
            raise ValueError("type mismatch")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("enum mismatch")
    if "const" in schema and value != schema["const"]:
        raise ValueError("const mismatch")
    for key in ("anyOf", "oneOf"):
        if key in schema:
            matches = 0
            for choice in schema[key]:
                try:
                    _validate(value, choice, depth + 1)
                    matches += 1
                except ValueError:
                    pass
            if matches == 0 or (key == "oneOf" and matches != 1):
                raise ValueError("union mismatch")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError("missing property")
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], depth + 1)
            elif schema.get("additionalProperties") is False:
                raise ValueError("extra property")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate(item, schema["additionalProperties"], depth + 1)
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", MAX_RESPONSE_BYTES):
            raise ValueError("array length")
        if "items" in schema:
            for item in value:
                _validate(item, schema["items"], depth + 1)
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", MAX_RESPONSE_BYTES):
            raise ValueError("string length")
    elif type(value) in (int, float):
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ValueError("number range")


def propose(prompt: str, output_schema: dict, run_dir: Path, timeout: int = 120,
            cancel_path: Path | None = None) -> dict:
    """Return a structured proposal and safe evidence, or raise ``ProviderError``.

    ``run_dir`` is a caller-owned, private evidence directory. It must not contain
    a symlink/junction. The CLI receives an empty child cwd and only prompt text.
    The pinned executable is rejected after an update until re-verification.
    """
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ProviderError("invalid_prompt", "The public prompt must contain 1 to 65,536 UTF-8 bytes.")
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ProviderError("invalid_timeout", "The provider timeout must be between 1 and 300 seconds.")
    try:
        encoded_schema = json.dumps(output_schema, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ProviderError("invalid_schema", "The output schema must be JSON.") from exc
    if not isinstance(output_schema, dict) or output_schema.get("type") != "object" or len(encoded_schema) > MAX_SCHEMA_BYTES:
        raise ProviderError("invalid_schema", "A bounded object output schema is required.")
    try:
        _check_schema(output_schema)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ProviderError("invalid_schema", "The output schema uses an unsupported constraint.") from exc
    run_dir = Path(run_dir).absolute()
    for ancestor in (run_dir, *run_dir.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise ProviderError("unsafe_run_directory", "The provider evidence path must not use links or junctions.")
    run_dir.mkdir(parents=True, exist_ok=True)
    call_dir = run_dir / ("provider-" + uuid.uuid4().hex)
    call_dir.mkdir()
    cwd = call_dir / "empty-workspace"
    cwd.mkdir()
    schema_path, response_path = call_dir / "output-schema.json", call_dir / "response.json"
    metadata_path = call_dir / "provider-metadata.json"
    schema_path.write_bytes(encoded_schema)
    started = time.monotonic()
    deadline = started + timeout
    def remaining() -> float:
        if cancel_path is not None and Path(cancel_path).exists():
            raise ProviderError("CANCELLED", "The provider call was cancelled.")
        result = deadline - time.monotonic()
        if result <= 0:
            raise ProviderError("timeout", "The provider exceeded its time limit.")
        return result
    metadata = {"name": "codex-chatgpt", "model": None, "cli_version": None,
                "cli_sha256": None, "catalog_sha256": CATALOG_SHA256,
                "duration_seconds": None, "usage": None, "cost": None,
                "transport": "existing-chatgpt-login", "tool_policy": "pinned-catalog-no-tools",
                "trust_boundary": "trusted-local-cli; tool suppression is not OS file isolation",
                "instruction_policy": dict(INSTRUCTION_POLICY),
                "inherited_guidance": INHERITED_GUIDANCE, "global_guidance": _guidance_presence(),
                "model_identity_source": "CLI header", "expected_resolved_model": EXPECTED_MODEL,
                "backend_identity_independently_verified": False,
                "application_retries": 0,
                "transport_retry_policy": "CLI defaults; all attempts bounded by the call timeout",
                "limits": {"timeout_seconds": timeout, "prompt_bytes": MAX_PROMPT_BYTES,
                           "response_bytes": MAX_RESPONSE_BYTES, "diagnostic_bytes": MAX_DIAGNOSTIC_BYTES,
                           "schema_bytes": MAX_SCHEMA_BYTES}, "status": "started"}
    evidence = {"response": str(response_path), "metadata": str(metadata_path), "schema": str(schema_path)}
    try:
        known_models = _verify_catalog()
        executable = _resolve_cli()
        metadata["cli_sha256"] = CLI_SHA256
        env = _environment()
        code, stdout, _ = _capture([executable, "--version"], cwd=cwd, env=env,
                                   timeout=min(10, remaining()), cancel_path=cancel_path)
        if code != 0 or stdout.strip() != CLI_VERSION:
            raise ProviderError("cli_mismatch", "The Codex CLI version differs from the verified release.")
        metadata["cli_version"] = CLI_VERSION
        code, stdout, stderr = _capture([executable, "login", "status"], cwd=cwd, env=env,
                                        timeout=min(10, remaining()), cancel_path=cancel_path)
        if code != 0 or "Logged in using ChatGPT" not in stdout + stderr:
            raise ProviderError("chatgpt_login_required", "The verified Codex CLI requires an existing ChatGPT login.")
        code, stdout, stderr = _capture(_argv(executable, cwd, schema_path, response_path),
                                         cwd=cwd, env=env, stdin=prompt.encode("utf-8"),
                                         timeout=remaining(), response=response_path, cancel_path=cancel_path)
        model = re.search(r"(?m)^model: ([A-Za-z0-9_.:-]+)\r?$", stderr)
        if model and model.group(1) in known_models:
            metadata["model"] = model.group(1)
            if model.group(1) != EXPECTED_MODEL:
                raise ProviderError("model_mismatch", "The CLI resolved a different model than the verified default.")
        usage = re.search(r"tokens used\s*\n([0-9,]+)", stderr)
        if usage:
            metadata["usage"] = {"reported_total_tokens": int(usage.group(1).replace(",", "")),
                                 "input_tokens": None, "output_tokens": None, "cached_input_tokens": None}
        if code != 0:
            lower = (stdout + stderr).lower()
            if any(term in lower for term in ("usage limit", "rate limit", "quota")):
                raise ProviderError("provider_limit", "The existing ChatGPT provider reported a usage limit.")
            if any(term in lower for term in ("unauthorized", "authentication", "login required", "token expired")):
                raise ProviderError("authentication_failed", "The existing ChatGPT authentication needs attention.")
            raise ProviderError("provider_failed", "The provider did not complete a structured proposal; no change was applied.")
        if metadata["model"] is None:
            raise ProviderError("missing_model_identity", "The provider did not report a recognized resolved model.")
        if not response_path.is_file() or response_path.is_symlink() or response_path.stat().st_size > MAX_RESPONSE_BYTES:
            raise ProviderError("invalid_response", "The provider did not produce a bounded response file.")
        try:
            def unique_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate key")
                    result[key] = value
                return result
            proposal = json.loads(response_path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite")))
            _validate(proposal, output_schema)
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise ProviderError("invalid_response", "The provider response failed the declared JSON schema.") from exc
        metadata["status"] = "completed"
        remaining()
        metadata["response_sha256"] = _digest(response_path)
        return {"proposal": proposal, "provider": metadata, "evidence": evidence}
    except (OSError, subprocess.SubprocessError) as exc:
        safe_error = ProviderError("provider_io_failed", "The provider could not complete its local evidence operation.", evidence)
        metadata["status"] = "failed"
        metadata["error"] = {"code": safe_error.code, "message": str(safe_error)}
        raise safe_error from exc
    except ProviderError as exc:
        metadata["status"] = "failed"
        metadata["error"] = {"code": exc.code, "message": str(exc)}
        exc.evidence = evidence
        # Discard malformed/partial output rather than retain unvalidated data.
        if response_path.is_file() and not response_path.is_symlink():
            response_path.unlink()
        raise
    finally:
        metadata["duration_seconds"] = round(time.monotonic() - started, 3)
        temp_metadata = metadata_path.with_suffix(".tmp")
        temp_metadata.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temp_metadata.replace(metadata_path)
