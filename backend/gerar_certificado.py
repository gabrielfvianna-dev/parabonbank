"""Gera um certificado HTTPS de DESENVOLVIMENTO (autoassinado).

Uso:
    python gerar_certificado.py 192.168.0.15

(troque pelo IP do seu computador; veja com o comando ipconfig)

Cria os arquivos certificados/cert.pem e certificados/chave.pem.
Depois, no .env:
    HTTPS_CERT=certificados/cert.pem
    HTTPS_KEY=certificados/chave.pem

ATENÇÃO: um certificado autoassinado criptografa a conexão, mas o celular
não confia nele automaticamente. Leia a seção HTTPS do docs/backend.md.
A chave privada (chave.pem) é secreta: a pasta certificados/ não vai para o Git.
"""

import ipaddress
import sys
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from app.config import PASTA_BACKEND

if __name__ == "__main__":
    ips = ["127.0.0.1", *sys.argv[1:]]
    pasta = PASTA_BACKEND / "certificados"
    pasta.mkdir(exist_ok=True)

    # Chave de curva elíptica P-256: forte e rápida.
    chave = ec.generate_private_key(ec.SECP256R1())
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Parabon Bank (desenvolvimento)")])
    agora = datetime.now(timezone.utc)

    # O certificado vale para "localhost" e para cada IP informado.
    nomes_validos = [x509.DNSName("localhost")] + [
        x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips
    ]

    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(minutes=5))
        .not_valid_after(agora + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(nomes_validos), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(chave, hashes.SHA256())
    )

    (pasta / "chave.pem").write_bytes(
        chave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (pasta / "cert.pem").write_bytes(certificado.public_bytes(serialization.Encoding.PEM))

    print(f"Certificado criado em {pasta} para: localhost, {', '.join(ips)}")
    print("Agora preencha HTTPS_CERT e HTTPS_KEY no .env e reinicie a API.")
