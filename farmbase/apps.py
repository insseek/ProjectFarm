from django.apps import AppConfig


class FarmbaseConfig(AppConfig):
    name = 'farmbase'

    def ready(self):
        # signals are imported, so that they are defined and can be used
        import farmbase.signals.handlers
