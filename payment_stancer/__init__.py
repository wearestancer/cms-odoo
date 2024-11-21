from odoo.addons.payment import reset_payment_provider
from odoo.addons.payment import setup_provider

from . import controllers
from . import models
from . import tests

__all__ = (
    "controllers",
    "models",
    "post_init_hook",
    "tests",
    "uninstall_hook",
)


def post_init_hook(cr, registry):
    setup_provider(cr, registry, "stancer")


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, "stancer")
