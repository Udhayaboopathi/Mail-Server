import ssl


def create_tls_context(cert_path: str = "/etc/ssl/certs/mail.crt", key_path: str = "/etc/ssl/private/mail.key") -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    return context
