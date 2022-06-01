from django.urls import path

from .views import SignCert

app_name = "appelflap_PKI"

urlpatterns = [
    path(r"sign-cert", SignCert.as_view(), name="sign-cert"),
]
