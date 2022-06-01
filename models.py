from django.db import models
from django.conf import settings
from django.utils.translation import gettext


class PackageSigningCert(models.Model):
    """
    Log of signed certificates. A bit bulky but super useful for auditing.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=False)
    signing_cert_sha256 = models.CharField(max_length=64)  # that'd be the hex-encoded sha256 of the DER-encoded cert
    signing_cert_CN = models.TextField()
    der_cert = models.BinaryField(null=True, blank=True)  # Why nullable? Well, we want to stuff the ID into the certificate itself. To get the ID, we first save() sans cert field set, then incorporate the DB primary key into the cert, then save the model instance again, this time with cert.

    class Meta:
        permissions = [
            ("sign_appelflap_p2p_packages", gettext("Can sign Appelflap packages for P2P distribution")),
        ]
