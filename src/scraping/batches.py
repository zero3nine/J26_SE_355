"""Recover saved raw and cleaned workflow batches by ID."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

import pandas as pd


_BATCH_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")


@dataclass
class SavedBatch:
    raw: pd.DataFrame
    parent_batch_id: str | None = None
    cleaned: pd.DataFrame | None = None
    cleaned_internal: pd.DataFrame | None = None
    warning: str | None = None


def _appended_path(root: Path, batch_id: str) -> Path:
    if not _BATCH_ID.fullmatch(batch_id):
        raise ValueError("Invalid batch ID.")
    return root / "data/raw/batches/appended" / f"batch_{batch_id}.json"


def _save_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_historical_batch(root: Path, batch_id: str, raw: pd.DataFrame) -> None:
    if not _BATCH_ID.fullmatch(batch_id):
        raise ValueError("Invalid batch ID.")
    target = root / "data/raw/historical_imports" / f"jobs_raw_{batch_id}.csv"
    _save_text(target, raw.to_csv(index=False))


def save_appended_batch(root: Path, batch_id: str, parent_batch_id: str, raw: pd.DataFrame) -> None:
    """Persist the exact appended scope and parent together in one atomic file."""
    target = _appended_path(root, batch_id)
    if not _BATCH_ID.fullmatch(parent_batch_id) or parent_batch_id == batch_id:
        raise ValueError("Invalid parent batch ID.")
    _save_text(target, json.dumps({"parent_batch_id": parent_batch_id, "raw_csv": raw.to_csv(index=False)}))


def _cleaned_paths(root: Path, batch_id: str) -> tuple[Path, Path, Path]:
    processed = root / "data/processed/batches"
    team = processed / f"jobs_clean_{batch_id}.csv"
    internal = processed / f"jobs_clean_internal_{batch_id}.csv"
    return team, internal, team.with_suffix(".manifest.json")


def _raw_digest(raw: pd.DataFrame) -> str:
    return sha256(raw.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def save_cleaned_batch(
    root: Path, batch_id: str, raw: pd.DataFrame, cleaned: pd.DataFrame, cleaned_internal: pd.DataFrame,
) -> None:
    """Save clean artifacts with a receipt tying them to the exact raw scope."""
    if not _BATCH_ID.fullmatch(batch_id):
        raise ValueError("Invalid batch ID.")
    team, internal, manifest = _cleaned_paths(root, batch_id)
    team_csv = cleaned.to_csv(index=False, lineterminator="\n")
    internal_csv = cleaned_internal.to_csv(index=False, lineterminator="\n")
    # Publish the expected hashes first so an interrupted write cannot look
    # like a legacy pair of unverified files.
    _save_text(manifest, json.dumps({
        "batch_id": batch_id,
        "raw_sha256": _raw_digest(raw),
        "team_sha256": sha256(team_csv.encode("utf-8")).hexdigest(),
        "internal_sha256": sha256(internal_csv.encode("utf-8")).hexdigest(),
    }))
    _save_text(team, team_csv)
    _save_text(internal, internal_csv)


def list_saved_batches(root: Path) -> list[str]:
    """Find raw batches in the existing live, historical, and appended stores."""
    raw = root / "data/raw"
    paths = {
        "jobs_raw_": [*raw.glob("batches/jobs_raw_*.csv"), *raw.glob("historical_imports/jobs_raw_*.csv")],
        "batch_": list(raw.glob("batches/appended/batch_*.json")),
    }
    ids = {
        path.stem.removeprefix(prefix)
        for prefix, files in paths.items()
        for path in files
        if _BATCH_ID.fullmatch(path.stem.removeprefix(prefix))
    }
    return sorted(ids, reverse=True)


def _read_records(source, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    if not required.issubset(frame.columns):
        raise ValueError("Unexpected batch columns.")
    return frame


def load_saved_batch(root: Path, batch_id: str) -> SavedBatch:
    appended = _appended_path(root, batch_id)
    raw_dir = root / "data/raw"
    raw_name = f"jobs_raw_{batch_id}.csv"
    paths = [raw_dir / name / raw_name for name in ("batches", "historical_imports")]
    parent_batch_id = None
    try:
        if appended.is_file():
            payload = json.loads(appended.read_text(encoding="utf-8"))
            parent_batch_id = payload["parent_batch_id"]
            if not _BATCH_ID.fullmatch(parent_batch_id) or parent_batch_id == batch_id:
                raise ValueError("Invalid parent batch ID.")
            source = StringIO(payload["raw_csv"])
        else:
            existing = [path for path in paths if path.is_file()]
            if len(existing) != 1:
                message = "Missing raw batch file." if not existing else "Multiple raw files have this batch ID."
                raise FileNotFoundError(message)
            source = existing[0]
        raw = _read_records(source, {"job_id", "job_title_raw"})
    except FileNotFoundError as error:
        raise ValueError(str(error)) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("The raw batch file is incomplete or unreadable.") from error

    batch = SavedBatch(raw, parent_batch_id)
    team, internal, manifest = _cleaned_paths(root, batch_id)
    if team.exists() or internal.exists() or manifest.exists():
        try:
            team_bytes, internal_bytes = team.read_bytes(), internal.read_bytes()
            if manifest.exists() and json.loads(manifest.read_text(encoding="utf-8")) != {
                "batch_id": batch_id,
                "raw_sha256": _raw_digest(raw),
                "team_sha256": sha256(team_bytes).hexdigest(),
                "internal_sha256": sha256(internal_bytes).hexdigest(),
            }:
                batch.warning = "The cleaned files do not match this raw batch. Clean the raw records again."
                return batch

            cleaned = _read_records(BytesIO(team_bytes), {"job_id", "job_description"})
            cleaned_internal = _read_records(
                BytesIO(internal_bytes), {"job_id", "job_description_clean", "extraction_status"},
            )
            identity = ["job_id"]
            if all("source_url" in frame for frame in (raw, cleaned, cleaned_internal)):
                identity.append("source_url")
            raw_keys = set(raw[identity].apply(lambda column: column.str.strip()).itertuples(index=False, name=None))
            internal_keys = set(cleaned_internal[identity].itertuples(index=False, name=None))
            exportable = cleaned_internal.loc[cleaned_internal["extraction_status"] != "excluded", identity]
            if not internal_keys.issubset(raw_keys) or not cleaned[identity].equals(exportable.reset_index(drop=True)):
                batch.warning = "The cleaned files do not match this raw batch. Clean the raw records again."
                return batch
            batch.cleaned = cleaned
            batch.cleaned_internal = cleaned_internal
        except (OSError, ValueError):
            batch.warning = "Cleaned files are incomplete or unreadable. The raw records can be cleaned again."
    return batch
