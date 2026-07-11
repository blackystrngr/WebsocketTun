import os
import logging
import subprocess
from pathlib import Path
from . import utils

class CloudflareCertManager:
    def __init__(self, domain, email, api_token, cert_source="acme", cert_file=None, key_file=None):
        self.domain = domain
        self.email = email
        self.api_token = api_token
        self.cert_source = cert_source  # 'cloudflare' or 'acme'
        self.cert_file = cert_file
        self.key_file = key_file
        self.le_dir = Path(f"/etc/letsencrypt/live/{domain}")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _install_certbot(self):
        """Install certbot and Cloudflare DNS plugin."""
        utils.print_info("Installing certbot and Cloudflare DNS plugin...")
        try:
            subprocess.run(
                "apt update && apt install -y certbot python3-certbot-dns-cloudflare",
                shell=True, check=True, executable="/bin/bash"
            )
            utils.print_success("Certbot installed.")
            return True
        except subprocess.CalledProcessError as e:
            utils.print_error(f"Certbot install failed: {e}")
            return False

    def _create_cloudflare_credentials(self):
        """Write Cloudflare API token to a temporary file for certbot."""
        cred_path = "/root/.cloudflare.ini"
        with open(cred_path, "w") as f:
            f.write(f"dns_cloudflare_api_token = {self.api_token}")
        os.chmod(cred_path, 0o600)
        return cred_path

    def request_certificate(self):
        if self.cert_source == "cloudflare":
            utils.print_info("Using Cloudflare Origin Certificate – no issuance needed.")
            if not self.cert_file or not self.key_file:
                utils.print_error("Cloudflare cert/key paths not set.")
                return False
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                utils.print_error(f"Certificate or key file not found: {self.cert_file} / {self.key_file}")
                return False
            utils.print_success("Cloudflare certificate files found.")
            return True
        else:
            # ACME via certbot
            utils.print_info(f"Requesting SSL certificate for {self.domain} via Certbot + Cloudflare DNS...")
            if not self._install_certbot():
                return False
            cred_file = self._create_cloudflare_credentials()
            cmd = (
                f"certbot certonly --dns-cloudflare --dns-cloudflare-credentials {cred_file} "
                f"-d {self.domain} --non-interactive --agree-tos --email {self.email} --expand"
            )
            if utils.run_command(cmd):
                utils.print_success("Certificate issued successfully via Certbot.")
                return True
            else:
                utils.print_error("Certbot certificate issuance failed.")
                return False

    def validate_certificate(self, cert_path, key_path, ca_path=None):
        if not cert_path or not os.path.exists(cert_path):
            utils.print_error("Certificate file not found for validation.")
            return False
        utils.print_info("Validating certificate against CA...")
        try:
            if ca_path and os.path.exists(ca_path):
                cmd = f"openssl verify -CAfile {ca_path} {cert_path}"
            else:
                cmd = f"openssl verify -CApath /etc/ssl/certs {cert_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                utils.print_success("Certificate is valid.")
                details_cmd = f"openssl x509 -in {cert_path} -noout -issuer -subject -dates"
                details = subprocess.run(details_cmd, shell=True, capture_output=True, text=True)
                if details.stdout:
                    utils.print_info("Certificate details:")
                    print(details.stdout)
                return True
            else:
                utils.print_error(f"Certificate validation failed: {result.stderr}")
                return False
        except Exception as e:
            utils.print_error(f"Validation error: {e}")
            return False

    def get_certificate_paths(self):
        if self.cert_source == "cloudflare":
            if self.cert_file and self.key_file:
                return self.cert_file, self.key_file, None
            return None, None, None
        else:
            # Certbot/Let's Encrypt
            cert = self.le_dir / "fullchain.pem"
            key = self.le_dir / "privkey.pem"
            if cert.exists() and key.exists():
                return str(cert), str(key), None
            self.logger.error("No certificate found in Let's Encrypt directory.")
            return None, None, None
