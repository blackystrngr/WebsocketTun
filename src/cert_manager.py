import os
import logging
import subprocess
import time
from pathlib import Path
from . import utils

class CloudflareCertManager:
    def __init__(self, domain, email, api_token, cert_source="acme", cert_file=None, key_file=None):
        self.domain = domain
        self.email = email
        self.api_token = api_token
        self.cert_source = cert_source
        self.cert_file = cert_file
        self.key_file = key_file
        self.acme_home = "/root/.acme.sh"
        self.acme_script = f"{self.acme_home}/acme.sh"
        self.le_dir = Path(f"/root/.acme.sh/{domain}")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _install_acme_sh(self):
        """Install acme.sh using the official install script (bash)."""
        utils.print_info("Installing acme.sh...")
        try:
            # Use the official install script, pipe to bash
            cmd = 'curl -s https://get.acme.sh | sh -s email={}'.format(self.email if self.email else "")
            # We'll run it with bash explicitly
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                executable="/bin/bash",
                env={**os.environ, "CF_Token": self.api_token}
            )
            utils.print_success("acme.sh installed.")
            return True
        except subprocess.CalledProcessError as e:
            utils.print_error(f"acme.sh install failed: {e}")
            return False

    def _ensure_acme_sh(self):
        """Ensure acme.sh is installed and available."""
        if os.path.exists(self.acme_script):
            return True
        return self._install_acme_sh()

    def request_certificate(self):
        if self.cert_source == "cloudflare":
            # Cloudflare Origin Certificate
            if not self.cert_file or not self.key_file:
                utils.print_error("Cloudflare cert/key paths not set.")
                return False
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                utils.print_error(f"Certificate or key file not found: {self.cert_file} / {self.key_file}")
                return False
            utils.print_success("Cloudflare certificate files found.")
            return True
        else:
            # ACME via acme.sh
            if not self._ensure_acme_sh():
                return False

            # Set Cloudflare token in environment
            os.environ["CF_Token"] = self.api_token

            # Build the acme.sh command
            cmd = [
                self.acme_script,
                "--issue",
                "-d", self.domain,
                "--dns", "dns_cf",
                "--force"  # Force renew even if existing
            ]
            if self.email and self.email.strip():
                cmd.extend(["--accountemail", self.email])
            else:
                # acme.sh can register without email using --register-unsafely-without-email
                # It's a flag for the '--register-account' step; but we can add it to the issue command.
                # Better: we run an explicit account registration first.
                # But acme.sh will auto-register if no account exists. Without email, it will prompt.
                # To avoid prompt, we can use --register-unsafely-without-email.
                # We'll run a separate registration command.
                reg_cmd = [
                    self.acme_script,
                    "--register-account",
                    "--register-unsafely-without-email",
                    "--force"
                ]
                utils.print_info("Registering acme.sh account without email.")
                try:
                    subprocess.run(reg_cmd, check=True, executable="/bin/bash")
                except subprocess.CalledProcessError as e:
                    utils.print_error(f"Account registration failed: {e}")
                    return False

            # Add -k to set key length? Not needed; we use default EC-256.

            # Issue the certificate
            utils.print_info(f"Issuing certificate for {self.domain} via acme.sh...")
            try:
                # Run with bash
                subprocess.run(cmd, check=True, executable="/bin/bash")
                utils.print_success("Certificate issued via acme.sh.")
                return True
            except subprocess.CalledProcessError as e:
                utils.print_error(f"acme.sh issuance failed: {e}")
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
            # acme.sh stores certs in ~/.acme.sh/<domain>/
            cert = self.le_dir / f"{self.domain}.cer"
            key = self.le_dir / f"{self.domain}.key"
            ca = self.le_dir / "ca.cer"
            if cert.exists() and key.exists():
                return str(cert), str(key), str(ca) if ca.exists() else None
            self.logger.error("No certificate found in acme.sh directory.")
            return None, None, None
