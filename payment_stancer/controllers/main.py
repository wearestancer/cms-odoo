from odoo import http
from odoo.http import request


class StancerController(http.Controller):
    _return_url = "/payment/stancer/return"

    @http.route(_return_url, type="http", methods=["GET"], auth="public", website=True)
    def stancer_return_from_checkout(self, **kwargs):
        """Process the notification data sent by Stancer after redirection from checkout.

        :param dict data: The notification data.
        """
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            ._get_tx_from_notification_data("stancer", kwargs)
        )
        tx_sudo._handle_notification_data("stancer", kwargs)
        return request.redirect("/payment/status")

    @http.route(
        "/stancer_provider_iframe_check",
        type="json",
        auth="public",
        website=True,
    )
    def stancer_is_iframe(self, provider_id, **kwargs):
        """Check the Iframe settings in Stancer provider."""
        stancer_provider = request.env["payment.provider"].sudo().browse(provider_id)

        return stancer_provider.is_iframe_enable

    @http.route("/prepare_stancer_iframe", type="json", auth="public", website=True)
    def prepare_stancer_iframe(self, **values):
        """This method prepares Iframe src link to provide Stancer Iframe Payment functionality."""
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("reference", "=", values["reference"]),
                    ("provider_code", "=", "stancer"),
                ]
            )
        )
        values = tx_sudo._get_processing_values()
        return tx_sudo._get_specific_rendering_values(values)
