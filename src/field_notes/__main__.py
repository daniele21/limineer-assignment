"""Load configuration, preflight everything, then extract and save results."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from anthropic import AnthropicError, transform_schema
from dotenv import load_dotenv

from .config import Config, load_config
from .extractor import extract_notes, load_prompt, render_user_prompt
from .schema import Extraction, Note


@dataclass
class PreparedRun:
    config: Config
    system_prompt: str
    user_prompt: str
    sites: list[tuple[str, list[Note]]]
    metadata: dict


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preflight(config_path: Path) -> PreparedRun:
    """Validate local inputs and build every request without creating an API client."""
    config_path = config_path.resolve()
    config = load_config(config_path)
    load_dotenv(config_path.parent / ".env", override=False)
    system = load_prompt(config.prompt.system_file)
    user = config.prompt.user_file.read_text(encoding="utf-8")
    if not system.strip():
        raise ValueError("System prompt must not be empty.")
    render_user_prompt(user, {})
    transform_schema(Extraction)  # Validate SDK schema transformation, without a request.
    input_text = config.input.sites_file.read_text(encoding="utf-8")
    data = json.loads(input_text)
    if not isinstance(data, dict) or not isinstance(data.get("sites"), list):
        raise ValueError("Sites file must contain an object with a 'sites' array.")
    sites = []
    seen = set()
    for site in data["sites"]:
        if not isinstance(site, dict) or not isinstance(site.get("site_id"), str) or not site["site_id"].strip():
            raise ValueError("Every site must have a nonempty string site_id.")
        site_id = site["site_id"]
        if site_id in seen:
            raise ValueError(f"Duplicate site_id: {site_id}")
        seen.add(site_id)
        if not isinstance(site.get("field_notes"), list):
            raise ValueError(f"{site_id}: field_notes must be an array.")
        notes = []
        for index, note in enumerate(site["field_notes"]):
            if not isinstance(note, dict):
                raise ValueError(f"{site_id}: each note must be an object.")
            notes.append(Note.model_validate({
                **note, "note_id": f"{site_id}:{index}", "source_site_id": site_id,
            }))
        render_user_prompt(user, {"opportunity_id": site_id, "notes": [note.model_dump(mode="json") for note in notes]})
        sites.append((site_id, notes))
    missing = set(config.input.site_ids) - seen
    if missing:
        raise ValueError(f"Unknown site IDs: {', '.join(sorted(missing))}")
    if config.input.site_ids:
        sites = [(site_id, notes) for site_id, notes in sites if site_id in config.input.site_ids]
    protected_paths = {config_path, config.input.sites_file, config.prompt.system_file, config.prompt.user_file}
    if config.output.path in protected_paths or config.output.path.is_dir():
        raise ValueError("Output path must be a file distinct from the input, prompts and config.")
    parent = config.output.path.parent
    while not parent.exists():
        parent = parent.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise ValueError("Output parent directory is not writable.")
    calls = sum(any(note.text.strip() for note in notes) for _, notes in sites)
    metadata = {
        "config_path": str(config_path),
        "config_sha256": sha256(config_path.read_text(encoding="utf-8")),
        "configuration": config.model_dump(mode="json"),
        "model": config.model.api_id,
        "system_prompt_sha256": sha256(system),
        "user_prompt_sha256": sha256(user),
        "input_sha256": sha256(input_text),
        "selected_site_ids": [site_id for site_id, _ in sites],
        "site_count": len(sites),
        "note_count": sum(len(notes) for _, notes in sites),
        "expected_api_calls": calls,
    }
    return PreparedRun(config, system, user, sites, metadata)


def run(config_path: Path, *, dry_run: bool = False) -> dict:
    prepared = preflight(config_path)
    key_present = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    if dry_run:
        return {
            "status": "preflight_passed", "api_calls_made": 0,
            "api_key_configured": key_present,
            "can_attempt_live": key_present or prepared.metadata["expected_api_calls"] == 0,
            "authentication": "not_checked",
            **prepared.metadata,
        }
    if prepared.metadata["expected_api_calls"] and not key_present:
        raise ValueError("ANTHROPIC_API_KEY is missing. Set it in the environment or .env beside the config.")
    config = prepared.config
    results = []
    started_at = datetime.now(timezone.utc).isoformat()
    for site_id, notes in prepared.sites:
        print(f"Extracting {site_id}...", file=sys.stderr)
        extracted = extract_notes(
            notes, opportunity_id=site_id, model=config.model.api_id,
            system_prompt=prepared.system_prompt, user_prompt=prepared.user_prompt,
            max_tokens=config.api.max_tokens, timeout_seconds=config.api.timeout_seconds,
            max_retries=config.api.max_retries,
        )
        results.append({
            "site_id": site_id, "field_notes": [note.model_dump(mode="json") for note in notes],
            **extracted.model_dump(mode="json"),
        })
    output = {"metadata": {"started_at": started_at, **prepared.metadata}, "results": results}
    config.output.path.parent.mkdir(parents=True, exist_ok=True)
    config.output.path.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} result(s) to {config.output.path}", file=sys.stderr)
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract field notes using a TOML configuration.")
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--dry-run", "--preflight", action="store_true", help="Validate all inputs without API calls or output writes.")
    args = parser.parse_args(argv)
    try:
        output = run(args.config, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(output, indent=2, ensure_ascii=False))
    except AnthropicError as exc:
        parser.exit(1, f"Anthropic request failed ({type(exc).__name__}). Check credentials, model access and quota.\n")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        parser.exit(1, f"Extraction failed: {exc}\n")


if __name__ == "__main__":
    main()
