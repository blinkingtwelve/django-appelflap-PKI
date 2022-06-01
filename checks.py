from django.core.checks import Warning, register

from .crypto_ops import load_and_check_deployment_materials, PKIException


@register()
def materials_check(app_configs, **kwargs):
    try:
        load_and_check_deployment_materials()
    except PKIException:
        return [Warning('Incorrectly configured PKI setup. You will not be able to sign Appelflap package signing certificates', hint="Review your settings.APPELFLAP_PKI dictionary and the appelflap_PKI app's README.md", id='appelflap_PKI.materialscheck.W001')]
    return []
