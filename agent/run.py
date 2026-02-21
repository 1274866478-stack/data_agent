"""Agent CLI entrypoint."""

import asyncio
import sys
from pathlib import Path

try:
    from .config import config
    from .sql_agent import interactive_mode, run_agent
except ImportError:
    from config import config
    from sql_agent import interactive_mode, run_agent

try:
    from .core.backend_runtime import ensure_backend_src_path
except ImportError:
    try:
        from core.backend_runtime import ensure_backend_src_path
    except ImportError:  # pragma: no cover - defensive fallback
        ensure_backend_src_path = None


def _has_backend_config() -> bool:
    if not callable(ensure_backend_src_path):
        return False
    try:
        return ensure_backend_src_path() is not None
    except Exception:
        return False


def _print_config_source() -> None:
    if _has_backend_config():
        print("[INFO] Backend configuration detected; using backend settings.")
        return

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print("[INFO] Using Agent .env configuration.")
    else:
        print("[WARN] .env not found; falling back to environment variables.")


def _validate_or_exit() -> None:
    try:
        config.validate_config()
    except ValueError as exc:
        print(f"[ERROR] Invalid configuration: {exc}")
        print("\nRequired variables:")
        print("- DEEPSEEK_API_KEY")
        print("- DATABASE_URL")
        print("\nExample:")
        print("DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxx")
        print("DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    _print_config_source()
    _validate_or_exit()

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"\n[QUERY] {question}\n")
        asyncio.run(run_agent(question))
        return

    print("\n[CHAT] Interactive mode. Type 'exit' or 'quit' to stop.\n")
    asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
