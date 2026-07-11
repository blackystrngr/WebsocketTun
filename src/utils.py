import os
import yaml
import logging
import subprocess
from dotenv import load_dotenv
from colorama import init, Fore, Style

init(autoreset=True)

def color_text(text, color=Fore.WHITE, style=Style.NORMAL):
    return f"{style}{color}{text}{Style.RESET_ALL}"

def print_header(text):
    print(Fore.CYAN + Style.BRIGHT + "=" * 50)
    print(Fore.CYAN + Style.BRIGHT + f"  {text}")
    print(Fore.CYAN + Style.BRIGHT + "=" * 50 + Style.RESET_ALL)

def print_success(text):
    print(Fore.GREEN + text)

def print_error(text):
    print(Fore.RED + text)

def print_info(text):
    print(Fore.YELLOW + text)

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def parse_port_list(value):
    if isinstance(value, list):
        return [int(p) for p in value]
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        if ',' not in value:
            return [int(value)]
        return [int(p.strip()) for p in value.split(',') if p.strip()]
    return []

def load_config():
    load_dotenv()
    config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f) or {}

    env_map = {
        "domain": "DOMAIN",
        "email": "EMAIL",
        "token": "CF_API_TOKEN",
        "ws_ports": "WS_PORTS",
        "tls_ports": "TLS_PORTS",
        "ssh_host": "SSH_HOST",
        "ssh_port": "SSH_PORT",
        "no_cert": "NO_CERT",
        "debug": "DEBUG",
    }
    # backward compatibility
    if "WS_PORT" in os.environ and "WS_PORTS" not in os.environ:
        os.environ["WS_PORTS"] = os.environ["WS_PORT"]
    if "TLS_PORT" in os.environ and "TLS_PORTS" not in os.environ:
        os.environ["TLS_PORTS"] = os.environ["TLS_PORT"]

    for key, env_var in env_map.items():
        val = os.getenv(env_var)
        if val is not None:
            if key in ("ws_ports", "tls_ports"):
                config[key] = parse_port_list(val)
            elif key == "ssh_port":
                config[key] = int(val)
            elif key in ("no_cert", "debug"):
                config[key] = val.lower() == "true"
            else:
                config[key] = val

    required = ["domain", "email", "token"]
    for req in required:
        if req not in config:
            raise ValueError(f"Missing required: {req}")

    config.setdefault("ws_ports", [8080])
    config.setdefault("tls_ports", [8443])
    config.setdefault("ssh_host", "127.0.0.1")
    config.setdefault("ssh_port", 22)
    return config

def ensure_acme_sh(email):
    acme_path = "/root/.acme.sh/acme.sh"
    if os.path.exists(acme_path):
        return True
    logging.info("Installing acme.sh...")
    try:
        subprocess.run(f'curl https://get.acme.sh | sh -s email={email}',
                       shell=True, check=True, executable="/bin/bash")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"acme.sh install failed: {e}")
        return False

def run_command(cmd, check=True):
    try:
        subprocess.run(cmd, shell=True, check=check, executable="/bin/bash")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {cmd}\nError: {e}")
        return False
