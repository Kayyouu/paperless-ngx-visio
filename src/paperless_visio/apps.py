"""
Django app configuration for Paperless Visio Parser

Registers the Visio parser with the document consumer system on app startup
"""

from django.apps import AppConfig


class PaperlessVisioConfig(AppConfig):
    """Configuration for the Paperless Visio Parser app"""

    name = "paperless_visio"
    verbose_name = "Paperless Visio Parser"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Called when Django app is ready

        Connects the visio_consumer_declaration signal handler to the
        document_consumer_declaration signal so Visio files are recognized
        and routed to the VisioDocumentParser
        """
        from documents.signals import document_consumer_declaration

        from .signals import visio_consumer_declaration

        # Register the Visio parser
        document_consumer_declaration.connect(visio_consumer_declaration)
