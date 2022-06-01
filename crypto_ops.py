from datetime import datetime
from binascii import hexlify

from django.conf import settings

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography import x509

from .rootcert import ROOTCERT_PEM
from .models import PackageSigningCert

MIN_VALIDITY = datetime(1970, 1, 1)
MAX_VALIDITY = datetime(2222, 1, 1)


class PKIException(Exception):
    pass


class PKIMisconfigured(PKIException):
    pass


class PKIUningestible(PKIException):
    pass


def load_and_check_deployment_materials():
    try:
        rootcert = x509.load_pem_x509_certificate(ROOTCERT_PEM, backend=default_backend())
        depcert = x509.load_pem_x509_certificate(open(settings.APPELFLAP_PKI['deployment_cert_path'], 'rb').read(), default_backend())
        depkey = serialization.load_pem_private_key(open(settings.APPELFLAP_PKI['deployment_key_path'], 'rb').read(), None, default_backend())
    except (KeyError, AttributeError, FileNotFoundError) as err:
        raise PKIMisconfigured(f"Error loading materials:\n {err}")

    # verify that depcert is signed with rootcert
    try:
        rootcert.public_key().verify(
            depcert.signature,
            depcert.tbs_certificate_bytes,
            PKCS1v15(),  # used with RSA, which for convenience we've standardised on as it's the only choice for old Androids
            depcert.signature_hash_algorithm,
        )
    except InvalidSignature:
        raise PKIMisconfigured("Intermediary certificate is not signed by Catalpa CA")

    # verify that the cert pubkey indeed goes with the cert private key
    if depkey.public_key().public_numbers() != depcert.public_key().public_numbers():
        raise PKIMisconfigured("Intermediary certificate is unrelated to declared private key")

    return (rootcert, depcert, depkey)


def get_deployment_cert():
    depcert, _depkey = load_and_check_deployment_materials()
    return depcert.public_bytes(encoding=serialization.Encoding.DER)


def sign_cert(cert: str, user):
    rootcert, depcert, depkey = load_and_check_deployment_materials()
    try:
        to_sign = x509.load_pem_x509_certificate(cert, backend=default_backend())
    except ValueError:
        raise PKIUningestible('Passed bytes do not look like a PEM-encoded x509 certificate')
    depcert_CN = depcert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
    to_sign_CN = to_sign.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
    new_cert = PackageSigningCert(user=user,
                                  signing_cert_sha256=hexlify(depcert.fingerprint(hashes.SHA256())).decode('ascii'),
                                  signing_cert_CN=depcert_CN[0].value
                                  )
    new_cert.save()  # Premature save, but it's to derive an ID, which will go into the cert as a serial number — as we have to have one, why not make it meaningful.
    device_cert = x509.CertificateBuilder().subject_name(
        x509.Name(to_sign_CN)
    ).issuer_name(
        x509.Name(depcert_CN)
    ).public_key(
        to_sign.public_key()
    ).serial_number(
        new_cert.id
    ).not_valid_before(
        MIN_VALIDITY
    ).not_valid_after(
        MAX_VALIDITY
    ).sign(
        depkey,
        hashes.SHA256(),
        default_backend()
    )
    new_cert.der_cert = device_cert.public_bytes(
        Encoding.DER
    )
    new_cert.save(update_fields=['der_cert'])
    return (device_cert, depcert, rootcert)


def pemicate(certs):
    return b''.join(map(lambda cert: cert.public_bytes(Encoding.PEM), certs))
