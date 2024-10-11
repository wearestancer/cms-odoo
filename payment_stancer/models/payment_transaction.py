import logging

from werkzeug import urls

from odoo import _
from odoo import fields
from odoo import models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from ..const import PAYMENT_PAGE
from ..controllers.main import StancerController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    refund_response = fields.Text(
        string="Refund Response",
        translate=True,
        readonly=True,
    )
    refund_processed = fields.Boolean(string="Refund Done", readonly=True)
    stancer_refund_id = fields.Char(string="Stancer Refund Id", readonly=True)
    is_refund_transfer = fields.Boolean(string="Is Refund", readonly=True)
    main_tx_id = fields.Many2one(
        comodel_name="payment.transaction",
        string="Main Stancer Transaction",
        readonly=True,
    )
    stancer_refund_tx_ids = fields.One2many(
        comodel_name="payment.transaction",
        string="Stancer Refund Transactions",
        inverse_name="main_tx_id",
        readonly=True,
    )
    stancer_payment_status = fields.Char(
        string="Stancer Payment Status", readonly=True
    )
    is_partial_refund = fields.Boolean(string="Partially Refunded", readonly=True)
    is_full_refund = fields.Boolean(string="fully Refunded", readonly=True)
    refunded_amount = fields.Monetary(
        string="Refunded Amount",
        currency_field="currency_id",
        readonly=True,
        default=0.0,
    )

    # === ACTION METHODS ===#

    def action_stancer_refund(self):
        """Pop-up the wizard to process refund"""

        self.ensure_one()
        stancer_provider = (
            self.env["payment.provider"].sudo().search([("code", "=", "stancer")])
        )
        stancer_payment_id = self.provider_reference
        endpoint = "/v1/checkout/" + stancer_payment_id
        payment_response = stancer_provider._stancer_make_request(
            endpoint, method="GET"
        )
        _logger.warning(
            "\n\n-------------payment_response-------------\n\n%s\n\n",
            str(payment_response),
        )
        self.stancer_payment_status = payment_response.get("status")
        remaining_amount = float_round(
            self.amount - self.refunded_amount,
            precision_digits=2,
            rounding_method="HALF-UP",
        )
        view = self.env.ref("payment_stancer.process_stancer_refund_form_view")
        return {
            "name": _("Process Stancer Refund"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "process.stancer.refund",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": {
                "default_tx_id": self.id,
                "default_full_refund_amount": remaining_amount,
            },
        }

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def _get_specific_rendering_values(self, processing_values):
        """
        Override of payment to return Stancer rendering values.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)

        if self.provider_code != "stancer":
            return res

        _logger.warning(processing_values)

        base_url = self.provider_id.get_base_url()
        base_return_url = urls.url_join(base_url, StancerController._return_url)
        arguments = urls.url_encode({"reference": self.reference})
        return_url = f"{base_return_url}?{arguments}"

        if self.provider_reference is False or self.provider_reference is None:
            payload = {
                "order_id": self.reference,
                "amount": float_round(
                    self.amount * 100,
                    precision_digits=2,
                    rounding_method="HALF-UP",
                ),
                "currency": self.currency_id.name.lower(),
                "auth": True,
            }

            stancer_payment = self.provider_id._stancer_make_request(
                "/v1/checkout",
                payload=payload,
                method="POST",
            )

            self.provider_reference = stancer_payment["id"]
            _logger.warning(stancer_payment)

        rendering_values = {
            "api_url": urls.url_join(
                PAYMENT_PAGE,
                f"/{self.provider_id.stancer_key_client}/{self.provider_reference}",
            ),
            "return_url": return_url,
        }

        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """
        Get payment status from Paytabs.

        :param provider_code: The code of the provider handling the transaction.
        :param notification_data: The data received from Paytabs notification.
        :return: The transaction matching the reference.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        _logger.warning(notification_data)

        if provider_code != "stancer":
            return tx

        reference = notification_data.get("reference", False)

        if not reference:
            raise ValidationError(_("Stancer: No reference found."))

        tx = self.search(
            [("reference", "=", reference), ("provider_code", "=", "stancer")]
        )

        if not tx:
            raise ValidationError(
                _("Stancer: No transaction found matching reference %s.") % reference
            )

        _logger.warning(tx)

        return tx

    def _process_notification_data(self, notification_data):
        """Update the transaction state and the provider reference based on the notification data.

        This method should usually not be called directly. The correct method to call upon receiving
        notification data is :meth:`_handle_notification_data`.

        For a provider to handle transaction processing, it must overwrite this method and process
        the notification data.

        Note: `self.ensure_one()`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        self.ensure_one()
        super()._process_notification_data(notification_data)
        stancer_provider = self.provider_id
        stancer_payment_id = self.provider_reference

        request_url = "/v1/checkout/" + stancer_payment_id
        payment_stancer = stancer_provider._stancer_make_request(
            request_url,
            method="GET",
        )
        _logger.info(
            "Stancer Payment :\"%s\" status : %s",
            str(payment_stancer["id"]),
            str(payment_stancer.get("status"))
            )
        response = payment_stancer["response"]
        status = payment_stancer["status"]

        if response != "00" or status in (
                "canceled",
                "disputed",
                "failed",
                "refused",
            ):
            self._process_unsucessful_payment(status,response)
            return
        self._process_sucessful_payment(status)


    def _process_sucessful_payment(self,status):
        """ Process a payment who suceeded.

        :param string status: The status of the sucessful payment.
        """
        # payment = self._create_payment(**{"payment_reference": self.reference})
        # self.payment_id = payment.id
        self.stancer_payment_status = status
        self.state_message = (
            self.env["stancer.response"].sudo()
            .search([("response_code", "=", "00-successful")])
            .response_message
        )
        self._set_done()

    def _process_unsucessful_payment(self,status,response):
        """Set the error message for a failed payment

        :param string status: The status of the unsucessful payment .
        :param string response: The response Code of the unsucessful payment.
        """
        response_message = (
            self.env["stancer.response"].sudo()
            .search([("response_code", "=", response)])
            .response_message
        )
        self.stancer_payment_status = status
        self.state_message = (
            response_message
            if response_message
            else "The payment has been refused [Response CODE: 05, Message: Do not Honor]"
        )
        self.stancer_payment_status = status
        self._set_error(f"Invalid payment status: {status}, response code: {response}")
