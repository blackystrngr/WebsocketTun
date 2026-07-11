import os
import logging
import subprocess
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
        utils.print_info(f"Requesting SSL certificate for {self.domain}...")
        if not utils.ensure_acme_sh(self.email):
            return False
        os.environ["CF_Token"] = self.api_token
        if not utils.run_command("export CF_Token"):
            return False
        acme_sh = "/root/.acme.sh/acme.sh"
        cmd = f'{acme_sh} --issue -d {self.domain} --dns dns_cf --force'
        if utils.run_command(cmd):
            utils.print_success(f"Certificate issued successfully.")
            return True
        return False

    def validate_certificate(self, cert_path, key_path, ca_path=None):
        """Validate certificate against CA using openssl verify."""
        if not cert_path or not os.path.exists(cert_path):
            utils.print_error("Certificate file not found for validation.")
            return False

        utils.print_info("Validating certificate against CA...")
        try:
            # Build openssl verify command
            if ca_path and os.path.exists(ca_path):
                cmd = f"openssl verify -CAfile {ca_path} {cert_path}"
            else:
                # Use system CA bundle if no CA file
                cmd = f"openssl verify -CApath /etc/ssl/certs {cert_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                utils.print_success(f"Certificate is valid.")
                # Show certificate details (expiry, issuer, etc.)
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
