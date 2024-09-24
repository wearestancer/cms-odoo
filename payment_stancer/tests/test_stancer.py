from odoo.addons.payment_stancer.tests.common import StancerCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestStancerPayment(StancerCommon):
    def test_incompatible_with_unsupported_currencies(self):
        """Test that Stancer providers are filtered out from compatible providers when the
        currency is not supported."""
        compatible_providers = self.env["payment.provider"]._get_compatible_providers(
            self.company_id,
            self.partner.id,
            self.amount,
            currency_id=self.env.ref("base.AFN").id,
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_get_supported_currencies(self):
        """Test the method that get default supported currencies"""
        supported_currencies = self.provider._get_supported_currencies()
        self.assertEqual(supported_currencies.name, "EUR")

    def test_get_default_payment_method_codes(self):
        """Test the method that get default payment method codes"""
        default_payment_method_codes = self.provider._get_default_payment_method_codes()
        self.assertEqual(
            default_payment_method_codes, ["stancer", "visa", "mastercard", "cb"]
        )

    def test_get_tx_from_notification_data(self):
        """Testing method that will test data from notification data and method does not return False"""
        tx = self._create_transaction("redirect")
        self.notification_data.update({"order_id": tx.reference})
        data_return = tx._get_tx_from_notification_data(
            "stancer", self.notification_data
        )
        self.assertNotEqual(tx, None)
