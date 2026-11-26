"""Restart or shut down the Pi.

Needs the sudo rule in deploy/enviro-power.sudoers, which allows exactly these
two commands without a password.
"""
import subprocess

COMMANDS = {
    'restart': ['sudo', '-n', '/usr/bin/systemctl', '--no-block', 'reboot'],
    'shutdown': ['sudo', '-n', '/usr/bin/systemctl', '--no-block', 'poweroff'],
}


def run(action):
    """Queue the restart or shutdown. Raises RuntimeError if it is refused."""
    try:
        result = subprocess.run(COMMANDS[action], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(str(exc))
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'exit code {}'.format(result.returncode))
