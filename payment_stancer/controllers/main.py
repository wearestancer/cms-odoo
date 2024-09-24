import logging

from werkzeug import urls

from odoo import http
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.payment_stancer import const
from odoo.fields import Command
from odoo.http import request
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class StancerController(http.Controller):
    _return_url = "/payment/stancer/return"

    @http.route(_return_url, type="http", methods=["GET"], auth="public", website=True)
    def stancer_return_from_checkout(self, **kwargs):
        """Process the notification data sent by Stancer after redirection from checkout.

        :param dict data: The notification data.
        """
        order = request.website.sale_get_order()

        stancer_provider = (
            request.env["payment.provider"].sudo().search([("code", "=", "stancer")])
        )
        stancer_response = request.env["stancer.response"]
        payment_method_line = (
            stancer_provider.journal_id.inbound_payment_method_line_ids.filtered(
                lambda l: l.code == stancer_provider._get_code()
            )
        )
        last_transaction_of_order = (
            request.env["payment.transaction"]
            .sudo()
            .search(
                [("reference", "ilike", order.name)],
                order="create_date desc",
                limit=1,
            )
        )
        stancer_payment_id = last_transaction_of_order.provider_reference

        request_url = "/v1/checkout/" + stancer_payment_id
        payment_response = stancer_provider._stancer_make_request(
            request_url,
            method="GET",
        )
        _logger.warning("\n\n\n RESPONSE -----------> \n\n\n %s", str(payment_response))

        response = payment_response.get("response")
        status = payment_response.get("status")

        if response == "00":
            if status not in (
                "canceled",
                "disputed",
                "failed",
                "refused",
            ):
                order.sudo().action_confirm()
                payment_values = {
                    "amount": float_round(
                        payment_response["amount"] / 100,
                        precision_digits=2,
                        rounding_method="HALF-UP",
                    ),
                    "payment_type": "inbound",
                    "currency_id": last_transaction_of_order.currency_id.id,
                    "partner_id": last_transaction_of_order.partner_id.commercial_partner_id.id,
                    "partner_type": "customer",
                    "journal_id": stancer_provider.journal_id.id,
                    "company_id": stancer_provider.company_id.id,
                    "payment_method_line_id": payment_method_line.id,
                    "payment_transaction_id": last_transaction_of_order.id,
                    "ref": last_transaction_of_order.reference,
                }

                payment = request.env["account.payment"].sudo().create(payment_values)

                last_transaction_of_order.payment_id = payment.id
                last_transaction_of_order._set_done()
                last_transaction_of_order.stancer_payment_status = status
                last_transaction_of_order.state_message = (
                    stancer_response.sudo()
                    .search([("response_code", "=", "00-successful")])
                    .response_message
                )

                payment.sudo().action_post()

                if not stancer_provider.is_iframe_enable:
                    order.sudo()._send_order_confirmation_mail()
                    invoice = order.sudo()._create_invoices()
                    invoice.sudo().action_post()

                if stancer_provider.is_iframe_enable:
                    order.sudo()._send_order_confirmation_mail()
                    last_transaction_of_order.sudo()._finalize_post_processing()
                    invoice = order.sudo()._create_invoices()
                    invoice.sudo().action_post()

                    return request.redirect("/shop/payment/validate")
            else:
                last_transaction_of_order.state_message = (
                    stancer_response.sudo()
                    .search([("response_code", "=", "00-unsuccessful")])
                    .response_message
                )
                last_transaction_of_order.stancer_payment_status = status
        else:
            response_message = (
                stancer_response.sudo()
                .search([("response_code", "=", response)])
                .response_message
            )
            last_transaction_of_order.stancer_payment_status = status
            last_transaction_of_order.state_message = (
                response_message
                if response_message
                else "The payment has been refused [Response CODE: 05, Message: Do not Honor]"
            )

        return request.redirect("/payment/status")

    @http.route(
        "/stancer_provider_iframe_check",
        type="json",
        auth="public",
        website=True,
    )
    def stancer_provider_iframe_check(self, stancer_id, **kwargs):
        stancer_provider = request.env["payment.provider"].sudo().browse(stancer_id)

        if stancer_provider.is_iframe_enable:
            return True
        else:
            return False

    @http.route("/prepare_stancer_iframe", type="json", auth="public", website=True)
    def prepare_stancer_iframe(self, stancer_id, **kwargs):
        """This method prepares Iframe src link to provide Stancer Iframe Payment functionality"""

        stancer_provider = request.env["payment.provider"].sudo().browse(stancer_id)
        order = request.website.sale_get_order()
        payload = {
            "order_id": order.name,
            "amount": float_round(
                order.amount_total * 100,
                precision_digits=2,
                rounding_method="HALF-UP",
            ),
            "currency": order.currency_id.name.lower(),
            "auth": True,
        }
        payment_link_data = stancer_provider._stancer_make_request(
            "/v1/checkout",
            payload=payload,
            method="POST",
        )
        _logger.warning(
            "\n\n\n RESPONSE -----------> \n\n\n %s\n\n\n",
            str(payment_link_data),
        )
        transaction_len = len(order.transaction_ids)
        token_id = None
        tokenization_requested = False
        tokenize = bool(
            # Don't tokenize if the user tried to force it through the browser's developer tools
            stancer_provider.allow_tokenization
            # Token is only created if required by the flow or requested by the user
            and (
                stancer_provider._is_tokenization_required(**kwargs)
                or tokenization_requested
            )
        )
        transaction_by_stancer = (
            request.env["payment.transaction"]
            .sudo()
            .create(
                {
                    "provider_id": stancer_provider.id,
                    "payment_method_id": request.env["payment.method"]
                    .search([("code", "=", "stancer")])
                    .id,
                    "partner_id": order.partner_id.id,
                    "reference": (
                        order.name
                        if transaction_len < 1
                        else order.name + "-" + str(transaction_len)
                    ),
                    "amount": order.amount_total,
                    "state": "error",
                    "token_id": token_id,
                    "operation": "online_direct",
                    "tokenize": tokenize,
                    "currency_id": order.currency_id.id,
                    "provider_reference": payment_link_data["id"],
                    "landing_route": "/shop/payment/validate",
                    "sale_order_ids": [Command.set([order.id])],
                }
            )
        )
        PaymentPostProcessing.monitor_transaction(transaction_by_stancer)
        order.transaction_ids = [(4, transaction_by_stancer.id)]
        request.session["__website_sale_last_tx_id"] = transaction_by_stancer.id
        transaction_by_stancer._get_processing_values()
        iframe_url = urls.url_join(
            const.PAYMENT_PAGE,
            f"/{stancer_provider.stancer_key_client}/{payment_link_data['id']}",
        )

        return iframe_url
