from django.http.response import HttpResponseBadRequest, HttpResponse
from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .crypto_ops import PKIUningestible, sign_cert, pemicate

require_permission = getattr(settings, 'APPELFLAP_PKI', {}).get("require_permission", False)


@method_decorator(csrf_exempt, name="dispatch")
class SignCert(View):
    http_method_names = ('post',)

    def post(self, request):
        if request.content_type != "application/x-pem-file":
            return HttpResponseBadRequest("Please post a PEM-encoded certificate.")
        if not request.user.is_authenticated:
            return HttpResponse("User is not authenticated", status=401, content_type="text/plain")
        if require_permission and not request.user.has_perm('appelflap_PKI.sign_appelflap_p2p_packages'):
            return HttpResponse("User doesn't have package signing permission", status=403, content_type="text/plain")
        try:
            certs = sign_cert(request.body, request.user)
        except PKIUningestible:
            return HttpResponseBadRequest("The offered cert is not appetizing.")
        return HttpResponse(pemicate(certs), content_type='application/x-pem-file')
