import os
import yaml
import logging
import subprocess
from dotenv import load_dotenv

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def parse_port_list(value):
    """Convert comma-separated string or int to list of ints."""
    if isinstance(value, list):
        return [int(p) for p in value]
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        # try as single int
        if ',' not in value:
            return [int(value)]
        # split by comma
        parts = [p.strip() for p in value.split(',') if p.strip()]
        return [int(p) for p in parts]
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
    # Also support old single-port names for backward compatibility
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

    # Ensure required
    required = ["domain", "email", "token"]
    for req in required:
        if req not in config:
            raise ValueError(f"Missing required configuration: {req}")

    # Default ports if not set
    if "ws_ports" not in config:
        config["ws_ports"] = [8080]
    if "tls_ports" not in config:
        config["tls_ports"] = [8443]
    if "ssh_host" not in config:
        config["ssh_host"] = "127.0.0.1"
    if "ssh_port" not in config:
        config["ssh_port"] = 22

    return config

# ... (ensure_acme_sh and run_command remain unchanged)
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
