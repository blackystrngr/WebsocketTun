import os
import logging
from pathlib import Path
from . import utils

class CloudflareCertManager:
    def __init__(self, domain, email, api_token):
        self.domain = domain
        self.email = email
        self.api_token = api_token
        self.cert_dir = Path(f"/root/.acme.sh/{domain}")
        self.logger = logging.getLogger(self.__class__.__name__)

    def request_certificate(self):
        self.logger.info(f"Requesting SSL for {self.domain}")
        if not utils.ensure_acme_sh(self.email):
            return False
        os.environ["CF_Token"] = self.api_token
        if not utils.run_command("export CF_Token"):
            return False
        acme_sh = "/root/.acme.sh/acme.sh"
        cmd = f'{acme_sh} --issue -d {self.domain} --dns dns_cf --force'
        if utils.run_command(cmd):
            self.logger.info("Certificate issued.")
            return True
        return False

    def get_certificate_paths(self):
        cert = self.cert_dir / f"{self.domain}.cer"
        key = self.cert_dir / f"{self.domain}.key"
        ca = self.cert_dir / "ca.cer"
        if cert.exists() and key.exists():
            return str(cert), str(key), str(ca)
        # fallback
        le_dir = Path("/etc/letsencrypt/live") / self.domain
        le_cert = le_dir / "fullchain.pem"
        le_key = le_dir / "privkey.pem"
        if le_cert.exists() and le_key.exists():
            return str(le_cert), str(le_key), None
        self.logger.error("No certificate found.")
        return None, None, None
