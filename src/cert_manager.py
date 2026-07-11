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
        self.cert_dir = Path(f"/root/.acme.sh/{domain}")
        self.logger = logging.getLogger(self.__class__.__name__)

    def request_certificate(self):
        if self.cert_source == "cloudflare":
            utils.print_info("Using Cloudflare Origin Certificate – no issuance needed.")
            # Just verify files exist
            if not self.cert_file or not self.key_file:
                utils.print_error("Cloudflare cert/key paths not set.")
                return False
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                utils.print_error(f"Certificate or key file not found: {self.cert_file} / {self.key_file}")
                return False
            utils.print_success("Cloudflare certificate files found.")
            return True
        else:
            # ACME (Let's Encrypt)
            utils.print_info(f"Requesting SSL certificate for {self.domain} via ACME...")
            if not utils.ensure_acme_sh(self.email):
                return False
            os.environ["CF_Token"] = self.api_token
            if not utils.run_command("export CF_Token"):
                return False
            acme_sh = "/root/.acme.sh/acme.sh"
            cmd = f'{acme_sh} --issue -d {self.domain} --dns dns_cf --force'
            if utils.run_command(cmd):
                utils.print_success("Certificate issued successfully.")
                return True
            return False

    def validate_certificate(self, cert_path, key_path, ca_path=None):
        """Validate certificate using openssl verify."""
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
            # Use the provided files
            if self.cert_file and self.key_file:
                return self.cert_file, self.key_file, None
            return None, None, None
        else:
            # ACME: look in acme.sh directory
            cert = self.cert_dir / f"{self.domain}.cer"
            key = self.cert_dir / f"{self.domain}.key"
            ca = self.cert_dir / "ca.cer"
            if cert.exists() and key.exists():
                return str(cert), str(key), str(ca) if ca.exists() else None
            # fallback Let's Encrypt
            le_dir = Path("/etc/letsencrypt/live") / self.domain
            le_cert = le_dir / "fullchain.pem"
            le_key = le_dir / "privkey.pem"
            if le_cert.exists() and le_key.exists():
                return str(le_cert), str(le_key), None
            self.logger.error("No certificate found.")
            return None, None, None
