"""Entry point for `python -m greyhawk_tools.session_notetaker`."""

import sys
from .session import GreyhawkSession


def main():
    try:
        session = GreyhawkSession()
        if "--post" in sys.argv:
            idx = sys.argv.index("--post")
            date_arg = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            session.post(date_arg)
        else:
            session.run()
    except ValueError as e:
        print(f"[!] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
