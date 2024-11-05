from decimal import Decimal
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
    stancer_payment_status = fields.Char(string="Scancer Payment Status", readonly=True)

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def get_amount_as_cent(self, float_amount):
        """Get the amount of the transaction in cents, as needed by the stancer API

        params: float_amount, the amount we want to convert
            (sometimes, it is not the transaction amount e.g. refunds)
        returns: int_amount, the amount converted as cents.
        """
        str_amount = Decimal(float_amount * pow(10, self.currency_id.decimal_places))

        return int(str_amount)

    def get_amount_as_currency(self, int_amount):
        """Get the amount of the transaction in the current currency.

        params: float_amount, the amount we want to convert
            (sometimes, it is not the transaction amount e.g. refunds)
        returns: float_amount, the amount converted in the current currency.
        """
        str_amount = round(
            Decimal(int_amount / pow(10, self.currency_id.decimal_places)),
            self.currency_id.decimal_places,
        )
        return float(str_amount)

    def _send_refund_request(self, amount_to_refund= None) :
        """Overrride the send refund request to make a refund request."""
        refund_tx = super()._send_refund_request(amount_to_refund)
        if self.provider_code != 'stancer':
            return refund_tx

        stancer_provider = self.provider_id
        refund_url = "/v1/refunds/"
        payload= {
            # refund amount is negative so we make it positive.
            "amount" : abs(self.get_amount_as_cent(refund_tx.amount)),
            "payment" : self.provider_reference
            }
        stancer_refund = stancer_provider._stancer_make_request(refund_url,payload,"POST")
        refund_tx.provider_reference= stancer_refund['id']
        if stancer_refund['status'] in(
            'refunded',
            'payment_canceled',
            'refund_sent',
            'to_refund'
        ):
            refund_tx._set_done()
            return
        refund_tx.set_error()

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
                "amount": self.get_amount_as_cent(self.amount),
                "currency": self.currency_id.name.lower(),
                "auth": True,
                "return_url": return_url if not self.provider_id.is_iframe_enable else ''
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
            "return_url": return_url
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

        if self.provider_code != 'stancer' :
            super()._process_notification_data(notification_data)
            return
        stancer_provider = self.provider_id
        stancer_payment_id = self.provider_reference

        request_url = "/v1/checkout/" + stancer_payment_id
        payment_stancer = stancer_provider._stancer_make_request(
            request_url,
            method="GET",
        )
        _logger.info(
            'Stancer Payment :"%s" status : %s',
            str(payment_stancer["id"]),
            str(payment_stancer.get("status")),
        )
        response = payment_stancer["response"]
        status = payment_stancer["status"]

        if response != "00" or status in (
            "canceled",
            "disputed",
            "failed",
            "refused",
        ):
            self._process_unsucessful_payment(status, response)
            return
        self._process_sucessful_payment(status)

    def _process_sucessful_payment(self, status):
        """Process a payment who suceeded.

        :param string status: The status of the sucessful payment.
        """
        self.stancer_payment_status = status
        self.state_message = (
            self.env["stancer.response"]
            .sudo()
            .search([("response_code", "=", "00-successful")])
            .response_message
        )
        self._set_done()

    def _process_unsucessful_payment(self, status, response):
        """Set the error message for a failed payment

        :param string status: The status of the unsucessful payment .
        :param string response: The response Code of the unsucessful payment.
        """
        response_message = (
            self.env["stancer.response"]
            .sudo()
            .search([("response_code", "=", response)])
            .response_message
        )
        self.stancer_payment_status = status
        self.state_message = (
            response_message
            if response_message
            else "The payment has been refused."
        )
        self.stancer_payment_status = status
        self._set_error(f"Invalid payment status: {status}, response code: {response}")
