from django.apps import AppConfig

class FileCollectorConfig(AppConfig):
    name = 'FileCollector'
    
    def ready(self):
        from . import signals 