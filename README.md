# 🐚 revshell-gen

`revshell-gen` is an offline TUI / CLI reverse shell one-liner generator, inspired by
[revshells.com](https://www.revshells.com/). It's meant to be used during authorized
penetration tests or CTFs, entirely from the terminal, without a browser.

Built to match the tooling conventions of
[Exegol-history](https://github.com/ThePorgs/Exegol-history) and
[web-server](https://github.com/lap1nou/web-server): `uv`, `textual` + `rich` for the TUI,
`argparse` for the CLI, `pytest` for tests.

## ✨ Features

- Textual **TUI**: search templates by name (Bash, Netcat, Python, Perl, PHP, Ruby, PowerShell,
  Socat, Node.js, Golang, Java, Awk, Telnet, OpenSSL, Lua, ...), live preview, copy to clipboard.
- **CLI** mode for scripting: `revshell-gen generate <id> --ip <ip> --port <port>`.
- The attacker **IP list is populated programmatically** from your local network interfaces
  (via `psutil`) — no more copy-pasting from `ip a` / `ifconfig` / `ipconfig`.
- Optional payload **encoding**: URL, double URL, base64, PowerShell `-enc` (base64 UTF-16LE).

## ⚙️ Install

```bash
uv tool install .
# or, for development:
uv sync
```

## 📖 Usage

```bash
# Launch the TUI (default)
revshell-gen
revshell-gen tui

# List available templates
revshell-gen list
revshell-gen list --os Windows
revshell-gen list --query bash

# List local IPv4 addresses (same data the TUI's IP dropdown uses)
revshell-gen ips

# Generate a one-liner non-interactively
revshell-gen generate bash-tcp --ip 10.10.14.5 --port 4444
revshell-gen generate powershell --ip 10.10.14.5 --port 4444 --encoding powershell-base64
```

### TUI keybinds

| Key | Action |
| --- | --- |
| `/` | Focus the search box |
| `c` | Copy the current payload to the clipboard |
| `q` | Quit |

A **Copy** button sits right next to the preview, and double-clicking a row in the payload
table also copies it straight to the clipboard.

## 🛠 Development

```bash
uv sync
uv run pytest
```

## ⚠️ Disclaimer

This project was made at nearly 100% by an LLM, however each line of code and each dependency was reviewed by a human.

For use only against systems you are authorized to test (pentest engagements, CTFs, your
own lab). The payload templates are the same well-known, publicly documented one-liners used
by tools like `revshells.com`, `msfvenom`, or PayloadsAllTheThings — nothing here is novel
exploit code.
