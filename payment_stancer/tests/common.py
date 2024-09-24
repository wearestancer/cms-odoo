from odoo.addons.payment.tests.common import PaymentCommon
from odoo.fields import Command


class StancerCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stancer = cls._prepare_provider(
            "stancer",
            update_values={
                "stancer_key_client": "ptest_HsybJXb5AAfIpWtIW02wiZeS",
                "stancer_key_secret": "stest_21wOsBSaQBq49HfQ3etN8J09",
                "stancer_payment_url": "https://payment.stancer.com",
                "stancer_api_url": "https://api.stancer.com",
                "payment_method_ids": [
                    Command.set(
                        [cls.env.ref("payment_stancer.payment_method_stancer").id]
                    )
                ],
            },
        )

        cls.provider = cls.stancer

        cls.notification_data = {"order_id": "order_name"}
