"""Typed TOML configuration. File paths are relative to the config, never the cwd."""

from pathlib import Path
import re
import tomllib

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelSettings(Section):
    name: str = Field(min_length=1)
    version: str | None = None

    @property
    def api_id(self) -> str:
        return resolve_model(self.name, self.version)


class PromptSettings(Section):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    system_file: Path
    user_file: Path


class InputSettings(Section):
    sites_file: Path
    site_ids: list[str] = Field(default_factory=list)


class OutputSettings(Section):
    path: Path


class ApiSettings(Section):
    max_tokens: int = Field(default=8192, gt=0, strict=True)
    timeout_seconds: float = Field(default=120.0, gt=0, strict=True)
    max_retries: int = Field(default=2, ge=0, strict=True)


class Config(Section):
    model: ModelSettings
    prompt: PromptSettings
    input: InputSettings
    output: OutputSettings
    api: ApiSettings = Field(default_factory=ApiSettings)


def resolve_model(model: str, version: str | None) -> str:
    if not model.strip():
        raise ValueError("Model name must not be blank.")
    if version is None:
        return model
    if not re.fullmatch(r"\d+(?:[.-]\d+)*", version):
        raise ValueError("Model version must be numeric, e.g. 5. Omit it for a full API ID.")
    suffix = version.replace(".", "-")
    if model.endswith(f"-{suffix}"):
        return model
    if re.search(r"-\d", model):
        raise ValueError("Use a base model name with version, or a full model ID without version.")
    return f"{model}-{suffix}"


def load_config(path: Path) -> Config:
    path = path.resolve()
    try:
        config = Config.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except ValidationError as exc:
        # Report field errors without echoing accidentally pasted credentials.
        errors = [f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
                  for item in exc.errors(include_input=False)]
        raise ValueError("Invalid configuration: " + "; ".join(errors)) from None
    config.model.api_id  # Validate model name/version before any API calls.
    for section, name in (
        (config.prompt, "system_file"), (config.prompt, "user_file"),
        (config.input, "sites_file"), (config.output, "path"),
    ):
        setattr(section, name, (path.parent / getattr(section, name)).resolve())
    return config
