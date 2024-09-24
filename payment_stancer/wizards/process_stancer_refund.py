import requests
from requests.auth import HTTPBasicAuth
from werkzeug import urls

from odoo import _
from odoo import fields
from odoo import models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ProcessStancerRefund(models.TransientModel):
    _name = "process.stancer.refund"
    _description = "Process Stancer Refund"

    tx_id = fields.Many2one(comodel_name="payment.transaction")
    is_full_refund = fields.Boolean(string="Full Refund")
    is_partial_refund = fields.Boolean(string="Partial Refund")
    currency_id = fields.Many2one(string="Currency", related="tx_id.currency_id")
    partial_refund_amount = fields.Monetary(
        string="Partial Amount", currency_field="currency_id"
    )
    full_refund_amount = fields.Monetary(
        string="Full Amount",
        currency_field="currency_id",
        readonly=True,
    )
    stancer_payment_status = fields.Char(
        string="Payment Status",
        related="tx_id.stancer_payment_status",
    )
    refunded_amount = fields.Monetary(
        string="Refunded Amount",
        related="tx_id.refunded_amount",
        readonly=True,
    )

    def process_refund(self):
        """Process the Full or Partial Refunds"""

        if self.is_partial_refund:
            if self.partial_refund_amount == 0.0:
                raise ValidationError(_("Amount must be greater than 0"))

            remaining_amount = float_round(
                self.tx_id.amount - self.tx_id.refunded_amount,
                precision_digits=2,
                rounding_method="HALF-UP",
            )

            if self.partial_refund_amount > remaining_amount:
                raise ValidationError(
                    _(
                        "You can not refund more than remaining Amount: %s",
                        str(remaining_amount),
                    )
                )

        stancer_provider = self.tx_id.provider_id
        payment_method_line = (
            stancer_provider.journal_id.inbound_payment_method_line_ids.filtered(
                lambda l: l.code == stancer_provider._get_code()
            )
        )
        amount = (
            float_round(
                self.full_refund_amount * 100,
                precision_digits=2,
                rounding_method="HALF-UP",
            )
            if self.is_full_refund
            else float_round(
                self.partial_refund_amount * 100,
                precision_digits=2,
                rounding_method="HALF-UP",
            )
        )
        stancer_payment_id = self.tx_id.provider_reference

        basic = HTTPBasicAuth(stancer_provider.stancer_key_secret, "")

        payload = {"payment": stancer_payment_id, "amount": amount}

        request_url = urls.url_join(stancer_provider.stancer_api_url, "/v1/refunds/")
        refund_request = requests.post(request_url, json=payload, auth=basic)
        refund_response = refund_request.json()

        if "id" in refund_response:
            self.tx_id.stancer_refund_id = refund_response.get("id")
            self.tx_id.refund_processed = True
            self.tx_id.refund_response = str(refund_response)
            refund_tx = self.env["payment.transaction"].create(
                {
                    "provider_id": stancer_provider.id,
                    "payment_method_id": self.env["payment.method"]
                    .search([("code", "=", "stancer")])
                    .id,
                    "partner_id": self.tx_id.partner_id.id,
                    "reference": f"Ref - {self.tx_id.reference} {str(len(self.tx_id.stancer_refund_tx_ids) + 1)}",
                    "amount": float_round(
                        -amount / 100,
                        precision_digits=2,
                        rounding_method="HALF-UP",
                    ),
                    "state": "done",
                    "currency_id": self.tx_id.currency_id.id,
                    "provider_reference": refund_response.get("payment"),
                    "stancer_refund_id": refund_response.get("id"),
                    "is_refund_transfer": True,
                    "refund_response": refund_response.get("status"),
                    "main_tx_id": self.tx_id.id,
                }
            )

            if self.is_full_refund:
                self.tx_id.is_full_refund = True
                self.tx_id.refunded_amount = float_round(
                    amount / 100,
                    precision_digits=2,
                    rounding_method="HALF-UP",
                )
            elif self.is_partial_refund:
                self.tx_id.is_partial_refund = True
                self.tx_id.refunded_amount += float_round(
                    amount / 100,
                    precision_digits=2,
                    rounding_method="HALF-UP",
                )
                if self.tx_id.amount == self.tx_id.refunded_amount:
                    self.tx_id.is_partial_refund = False
                    self.tx_id.is_full_refund = True

            payment_values = {
                "amount": float_round(
                    amount / 100,
                    precision_digits=2,
                    rounding_method="HALF-UP",
                ),
                "payment_type": "outbound",
                "currency_id": self.tx_id.currency_id.id,
                "partner_id": self.tx_id.partner_id.commercial_partner_id.id,
                "partner_type": "customer",
                "journal_id": stancer_provider.journal_id.id,
                "company_id": stancer_provider.company_id.id,
                "payment_method_line_id": payment_method_line.id,
                "payment_transaction_id": refund_tx.id,
                "ref": f"{self.tx_id.reference} Stancer Refund",
            }

            payment = self.env["account.payment"].sudo().create(payment_values)
            refund_tx.payment_id = payment.id
            payment.action_post()

        else:
            raise ValidationError(
                _("Request issue occurred.\n Error Response: %s", str(refund_response))
            )
