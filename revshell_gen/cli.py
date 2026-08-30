from __future__ import annotations

import argparse
import sys

import argcomplete
from rich.console import Console
from rich.table import Table

from revshell_gen.generator import Encoding, InvalidIPError, InvalidPortError, generate
from revshell_gen.network import list_ipv4_addresses
from revshell_gen.templates import TargetOS, find, search

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="revshell-gen",
        description="Offline reverse-shell one-liner generator (revshells.com, in your terminal).",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("tui", help="Launch the interactive TUI (default when run with no arguments).")

    list_parser = subparsers.add_parser("list", help="List available shell templates.")
    list_parser.add_argument("--query", "-q", default="", help="Filter by name/id.")
    list_parser.add_argument(
        "--os",
        choices=[o.value for o in TargetOS],
        default=None,
        help="Filter by target OS.",
    )

    subparsers.add_parser("ips", help="List local IPv4 addresses found on network interfaces.")

    gen_parser = subparsers.add_parser("generate", help="Generate a single reverse shell one-liner.")
    gen_parser.add_argument("template_id", help="Template id, see `revshell-gen list`.")
    gen_parser.add_argument("--ip", required=True, help="Attacker IP / hostname to connect back to.")
    gen_parser.add_argument("--port", "-p", type=int, required=True, help="Attacker listening port.")
    gen_parser.add_argument(
        "--encoding",
        "-e",
        choices=[e.value for e in Encoding],
        default=Encoding.RAW.value,
        help="Encode the payload (url, url-double, base64, powershell-base64).",
    )

    return parser


def _cmd_list(args: argparse.Namespace) -> int:
    os_filter = TargetOS(args.os) if args.os else None
    templates = search(query=args.query, os_filter=os_filter)

    table = Table(title="Reverse shell templates")
    table.add_column("id", style="cyan")
    table.add_column("name", style="bold")
    table.add_column("os")

    for template in templates:
        table.add_row(template.id, template.name, template.os.value)

    console.print(table)
    return 0


def _cmd_ips(_args: argparse.Namespace) -> int:
    addresses = list_ipv4_addresses()

    if not addresses:
        console.print("[yellow]No non-loopback IPv4 address found on this host.[/yellow]")
        return 0

    table = Table(title="Local IPv4 addresses")
    table.add_column("interface", style="cyan")
    table.add_column("ip", style="bold")

    for addr in addresses:
        table.add_row(addr.interface, addr.ip)

    console.print(table)
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    template = find(args.template_id)
    if template is None:
        console.print(f"[red]Unknown template id: {args.template_id}[/red]")
        console.print("Run `revshell-gen list` to see available ids.")
        return 1

    try:
        command = generate(template, args.ip, args.port, Encoding(args.encoding))
    except (InvalidIPError, InvalidPortError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    # soft_wrap: never insert newlines into the payload, even if it's wider
    # than the terminal -- the output must stay copy-paste safe.
    console.print(command, soft_wrap=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.command is None or args.command == "tui":
        from revshell_gen.app import RevshellApp

        RevshellApp().run()
        return 0

    if args.command == "list":
        return _cmd_list(args)
    if args.command == "ips":
        return _cmd_ips(args)
    if args.command == "generate":
        return _cmd_generate(args)

    parser.print_help()
    return 1
