"""Command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json

from . import __version__ as _VERSION
from . import config as config_mod
from .events import EventType
from .hardware import probe as hardware_probe
from .models.catalog import default_catalog
from .models.manager import ModelManager
from .session import SessionController


def _print_event(ev) -> None:
    if ev.type == EventType.PARTIAL:
        print(f"\r… {ev.text}", end="", flush=True)
    elif ev.type == EventType.FINAL:
        print(f"\n✓ {ev.text}", flush=True)
    elif ev.type.value.endswith("warning"):
        print(f"\n! {ev.text}", flush=True)


async def run_session(args) -> int:
    cfg = config_mod.Config.load()
    if args.engine:
        cfg.engine = args.engine

    controller = SessionController(
        cfg, on_event=_print_event, output=getattr(args, "output", None)
    )
    try:
        await controller.start()
    except Exception as e:
        print(f"Could not start session: {e}")
        return 1

    profile = hardware_probe.probe()
    print(
        f"LocalScribe running: engine={cfg.engine} model={controller.model_path} "
        f"cores={profile.physical_cores} ram_gb={profile.ram_bytes/(1024**3):.1f}"
    )
    print("Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await controller.stop()
        # Export readable TXT/JSON/SRT transcripts on exit.
        try:
            out_path = controller.export()
            print(f"\nSaved transcript to {out_path}")
        except Exception as e:
            print(f"\nCould not save transcript: {e}")
    return 0


async def run_tui(args) -> int:
    from .tui.session import LocalScribeApp

    cfg = config_mod.Config.load()
    if args.engine:
        cfg.engine = args.engine
    app = LocalScribeApp(cfg, output=getattr(args, "output", None))
    await app.run_async()
    if app.export_path:
        print(f"Saved transcript to {app.export_path}")
    return 0


def cmd_models_list(args) -> int:
    mgr = ModelManager()
    for e in mgr.list_models(default_catalog()):
        print(f"{e.name}  engine={e.engine} lang={e.language} installed={e.installed} size~{e.size_bytes}")
    return 0


def cmd_models_download(args) -> int:
    mgr = ModelManager()
    catalog = {e.name: e for e in default_catalog()}
    if args.name not in catalog:
        print("unknown model:", args.name)
        return 1
    path = mgr.download(catalog[args.name])
    print("installed to", path)
    return 0


def cmd_models_verify(args) -> int:
    mgr = ModelManager()
    print(mgr.verify_all())
    return 0


def cmd_probe(args) -> int:
    p = hardware_probe.probe()
    print(p.to_dict())
    return 0


def cmd_setup(args) -> int:
    from .config_wizard import run_wizard

    run_wizard()
    return 0


def cmd_version(args) -> int:
    print(f"localscribe {_VERSION}")
    return 0


def cmd_config(args) -> int:
    from dataclasses import asdict

    from .config import Config

    cfg = Config.load()
    if getattr(args, "wizard", False):
        from .config_wizard import run_wizard

        run_wizard(cfg)
        return 0
    print(json.dumps(asdict(cfg), indent=2))
    print(f"# {cfg.path()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="localscribe")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run dictation")
    r.add_argument("--engine", choices=["vosk", "whisper"], default=None)
    r.add_argument("--tui", action="store_true")
    r.add_argument("--output", default=None)
    r.set_defaults(func=lambda a: asyncio.run(run_tui(a) if a.tui else run_session(a)))

    m = sub.add_parser("models", help="model management")
    ms = m.add_subparsers(dest="mcommand", required=True)
    ml = ms.add_parser("list")
    ml.set_defaults(func=lambda a: cmd_models_list(a))
    md = ms.add_parser("download")
    md.add_argument("name")
    md.set_defaults(func=lambda a: cmd_models_download(a))
    mv = ms.add_parser("verify")
    mv.set_defaults(func=lambda a: cmd_models_verify(a))

    pr = sub.add_parser("probe")
    pr.set_defaults(func=lambda a: cmd_probe(a))

    st = sub.add_parser("setup", help="interactive configuration wizard")
    st.set_defaults(func=lambda a: cmd_setup(a))

    c = sub.add_parser("config", help="show or edit configuration")
    c.add_argument("--wizard", action="store_true", help="run interactive wizard")
    c.set_defaults(func=lambda a: cmd_config(a))

    v = sub.add_parser("version", help="print version")
    v.set_defaults(func=lambda a: cmd_version(a))

    p.add_argument("--version", action="version", version=f"localscribe {_VERSION}")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
