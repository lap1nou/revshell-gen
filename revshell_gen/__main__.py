from __future__ import annotations

import sys

from revshell_gen.cli import main as cli_main


def main() -> None:
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
