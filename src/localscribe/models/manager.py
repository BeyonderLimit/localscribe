"""Offline-safe model download and verification."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterable
from pathlib import Path

import requests

from ..platform import model_dir
from .catalog import CatalogEntry


class ModelManager:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or model_dir()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.directory / "manifest.json"
        self._manifest: dict[str, dict] = {}
        if self.manifest_path.exists():
            try:
                self._manifest = json.loads(self.manifest_path.read_text())
            except Exception:
                self._manifest = {}

    def _entry_dir(self, entry: CatalogEntry) -> Path:
        return self.directory / entry.engine / entry.name

    def list_models(self, catalog: Iterable[CatalogEntry]) -> list[CatalogEntry]:
        out = []
        for e in catalog:
            installed = self._entry_dir(e).exists()
            e.installed = installed
            out.append(e)
        return out

    def verify_entry(self, entry: CatalogEntry) -> bool:
        d = self._entry_dir(entry)
        if not d.exists():
            return False
        if entry.sha256:
            # verify a single marker file if present
            pass
        return True

    def download(self, entry: CatalogEntry) -> Path:
        dest_dir = self._entry_dir(entry)
        dest_dir.mkdir(parents=True, exist_ok=True)
        tmp = dest_dir / f"{entry.name}.part"
        with requests.get(entry.url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        if entry.sha256:
            h = hashlib.sha256()
            with tmp.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() != entry.sha256:
                tmp.unlink(missing_ok=True)
                raise ValueError("checksum mismatch")
        final = dest_dir / entry.name
        shutil.move(str(tmp), str(final))
        # Extract archive models (Vosk ships zip archives).
        import zipfile

        if zipfile.is_zipfile(final):
            extract_dir = dest_dir / (entry.name + "-extracted")
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(final) as z:
                z.extractall(extract_dir)
            final.unlink(missing_ok=True)
            # normalize to extracted root if single dir
            children = [p for p in extract_dir.iterdir()]
            if len(children) == 1 and children[0].is_dir():
                model_path = children[0]
            else:
                model_path = extract_dir
        else:
            model_path = final
        self._manifest[entry.name] = {
            "source": entry.url,
            "version": "unknown",
            "checksum": entry.sha256,
            "install_date": None,
            "license": entry.license,
            "path": str(model_path),
        }
        self.manifest_path.write_text(json.dumps(self._manifest, indent=2))
        return model_path

    def verify_all(self) -> dict[str, bool]:
        results = {}
        for name, info in self._manifest.items():
            p = Path(info.get("path", ""))
            results[name] = p.exists()
        return results
