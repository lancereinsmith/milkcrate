"""Security utilities and middleware for HTTPS and security headers.

Provides security headers, HTTPS redirects, and SSL/TLS configuration
for production deployments.
"""

import os

from flask import Flask, redirect, request


class SecurityHeaders:
    """Middleware for adding security headers to responses."""

    def __init__(self, app: Flask | None = None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize security headers middleware."""
        app.after_request(self.add_security_headers)

        # Add HTTPS redirect in production
        if app.config.get("ENV") == "production" or app.config.get("FORCE_HTTPS"):
            app.before_request(self.force_https)

    def add_security_headers(self, response):
        """Add security headers to all responses."""
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # HTTPS Strict Transport Security (only if using HTTPS)
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent caching of sensitive pages
        if request.endpoint and "admin" in request.endpoint:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    def force_https(self):
        """Redirect HTTP requests to HTTPS in production."""
        if (
            not request.is_secure
            and request.headers.get("X-Forwarded-Proto") != "https"
        ):
            # Don't redirect health check endpoints
            if request.endpoint in ["health", "status"]:
                return None

            # Redirect to HTTPS
            return redirect(request.url.replace("http://", "https://", 1), code=301)
        return None


def configure_ssl_context(app: Flask) -> tuple | None:
    """Configure SSL context for HTTPS support.

    Args:
        app: Flask application instance

    Returns:
        SSL context tuple (cert_file, key_file) or None
    """
    cert_file = app.config.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_FILE")
    key_file = app.config.get("SSL_KEY_FILE") or os.environ.get("SSL_KEY_FILE")

    if cert_file and key_file:
        # Verify files exist
        if os.path.exists(cert_file) and os.path.exists(key_file):
            app.logger.info(f"SSL configured with cert: {cert_file}")
            return (cert_file, key_file)
        app.logger.warning(f"SSL files not found: {cert_file}, {key_file}")

    return None


def generate_self_signed_cert(app: Flask, cert_dir: str | None = None) -> tuple | None:
    """Generate self-signed certificate for development.

    Args:
        app: Flask application instance
        cert_dir: Directory to store certificates

    Returns:
        SSL context tuple (cert_file, key_file) or None
    """
    try:
        import datetime

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        if cert_dir is None:
            cert_dir = app.instance_path

        cert_file = os.path.join(cert_dir, "milkcrate-cert.pem")
        key_file = os.path.join(cert_dir, "milkcrate-key.pem")

        # Check if certificates already exist
        if os.path.exists(cert_file) and os.path.exists(key_file):
            return (cert_file, key_file)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Milkcrate Development"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.DNSName("127.0.0.1"),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Write certificate file
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write private key file
        with open(key_file, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Set appropriate permissions
        os.chmod(key_file, 0o600)
        os.chmod(cert_file, 0o644)

        app.logger.info(f"Generated self-signed certificate: {cert_file}")
        return (cert_file, key_file)

    except ImportError:
        app.logger.warning(
            "cryptography package not available for self-signed certificates"
        )
        return None
    except Exception as e:
        app.logger.error(f"Failed to generate self-signed certificate: {e}")
        return None


# Global security headers instance
security_headers = SecurityHeaders()
