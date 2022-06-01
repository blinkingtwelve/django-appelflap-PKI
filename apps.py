from django.apps import AppConfig


class AppelflapPkiConfig(AppConfig):
    name = 'appelflap_PKI'

    def ready(self):
        from . import checks  # noqa
