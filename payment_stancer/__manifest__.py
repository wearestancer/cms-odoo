{
    "name": "Stancer",
    "version": "1.0.0",
    "category": "Accounting/Payment Providers",
    "sequence": 350,
    "summary": "A French payment provider covering France",
    "depends": ["payment"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_stancer_templates.xml",
        "data/payment_provider_data.xml",
        "data/stancer_response_data.xml",
        "views/payment_provider_views.xml",
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
