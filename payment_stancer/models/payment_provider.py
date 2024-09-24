import logging

import requests
from requests.auth import HTTPBasicAuth
from werkzeug.urls import url_join

from odoo import _
from odoo import fields
from odoo import models
from odoo.addons.payment_stancer import const
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("stancer", "Stancer")], ondelete={"stancer": "set default"}
    )
    stancer_key_client = fields.Char(
        string="stancer Key Client",
        help="The key solely used to identify the account with stancer.",
        required_if_provider="stancer",
    )
    stancer_key_secret = fields.Char(
        string="stancer Key Secret",
        required_if_provider="stancer",
        groups="base.group_system",
    )
    stancer_response_ids = fields.One2many(
        string="Stancer Response",
        comodel_name="stancer.response",
        inverse_name="payment_provider_id",
    )
    is_iframe_enable = fields.Boolean(string="Enable Iframe", default="true")

    # === COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "stancer").update(
            {
                "support_manual_capture": "full_only",
                "support_refund": "partial",
            }
        )

    # === BUSINESS METHODS ===#

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "stancer":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _stancer_make_request(self, endpoint, payload=None, method=""):
        """Make a request to Stancer API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        basic = HTTPBasicAuth(self.stancer_key_secret, "")
        url = url_join(const.API_HOST, endpoint)
        try:
            if method == "GET":
                response = requests.get(url, json=payload, auth=basic)
                _logger.warning(response.json())
            else:
                response = requests.post(url, json=payload, auth=basic)
                _logger.warning(response.json())
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s",
                    url,
                )
                raise ValidationError(
                    "Stancer: "
                    + _(
                        "The communication with the API failed. "
                        "Stancer gave us the following information: '%s'",
                        response.json().get("error", {}).get("description"),
                    )
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Stancer: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != "stancer":
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
