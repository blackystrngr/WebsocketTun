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
        "ws_port": "WS_PORT",
        "tls_port": "TLS_PORT",
        "ssh_host": "SSH_HOST",
        "ssh_port": "SSH_PORT",
        "no_cert": "NO_CERT",
        "debug": "DEBUG",
    }
    for key, env_var in env_map.items():
        val = os.getenv(env_var)
        if val is not None:
            if key in ("ws_port", "tls_port", "ssh_port"):
                val = int(val)
            elif key in ("no_cert", "debug"):
                val = val.lower() == "true"
            config[key] = val

    required = ["domain", "email", "token"]
    for req in required:
        if req not in config:
            raise ValueError(f"Missing required configuration: {req}")
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
