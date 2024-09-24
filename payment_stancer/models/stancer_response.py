from odoo import fields
from odoo import models


class StancerResponse(models.Model):
    _name = "stancer.response"
    _description = "Stancer Response"

    response_code = fields.Char(string="CODE")
    response_message = fields.Char(string="Message")
    payment_provider_id = fields.Many2one(comodel_name="payment.provider")
