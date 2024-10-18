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


def post_init_hook(env):
    setup_provider(env, "stancer")


def uninstall_hook(env):
    reset_payment_provider(env, "stancer")
