{
    "name": "Stancer",
    "version": "17.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "Stancer for Odoo",
    "depends": ["payment", "account", "sale_management", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/process_stancer_refund_form_view.xml",
        "views/payment_stancer_templates.xml",
        "data/payment_provider_data.xml",
        "data/stancer_response_data.xml",
        "views/payment_provider_views.xml",
        "views/payment_transaction_extend.xml",
        "views/payment_view_extend.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_stancer/static/src/js/stancer_iframe.js",
            "payment_stancer/static/src/scss/iframe.scss",
        ],
    },
    "images": ["images/main_screenshot.png"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "license": "Other OSI approved licence",
}
