"""Entry point for `python -m greyhawk_tools.image_analysis`."""

import argparse
import sys

from .analyzer import DEFAULT_PROMPT, analyze


def main():
    parser = argparse.ArgumentParser(
        prog="analyze_image", description="Describe an image with a vision model."
    )
    parser.add_argument("target", help="image URL or path to a local image file")
    parser.add_argument("-p", "--prompt", default=DEFAULT_PROMPT, help="what to ask about the image")
    parser.add_argument("--max-tokens", type=int, default=300)
    args = parser.parse_args()

    try:
        print(analyze(args.target, args.prompt, args.max_tokens))
    except (ValueError, FileNotFoundError) as e:
        print(f"[!] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
