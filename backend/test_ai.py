import argparse
import asyncio
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_engine import AIEngineService  # noqa: E402


def parse_history(raw_history: str | None) -> list[dict[str, object]]:
    if not raw_history:
        return []

    try:
        parsed = json.loads(raw_history)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON passed to --history: {exc}") from exc

    if not isinstance(parsed, list):
        raise SystemExit("--history must be a JSON array of role/content objects.")

    return parsed


async def run_test(message: str, history: list[dict[str, object]]) -> None:
    response = await AIEngineService.process_user_intent(message, history)
    print(response.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the EduByte Groq AI engine.")
    parser.add_argument(
        "--message",
        default="Explain the structure of an atom.",
        help="The latest user message to send to the AI engine.",
    )
    parser.add_argument(
        "--history",
        default="[]",
        help='JSON array of prior turns, for example: [{"role":"user","content":"Hi"}]',
    )

    args = parser.parse_args()
    history = parse_history(args.history)

    asyncio.run(run_test(args.message, history))


if __name__ == "__main__":
    main()