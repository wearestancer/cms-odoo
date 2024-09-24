API_HOST = "https://api.stancer.com"

SUPPORTED_CURRENCIES = [
    "EUR",
    "USD",
]

# Mapping of transaction states to stancer payment statuses.
PAYMENT_STATUS_MAPPING = {
    "pending": ["pending auth"],
    "done": ["successful"],
    "cancel": ["cancelled"],
    "error": ["failed"],
}

# The codes of the payment methods to activate when Stancer is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    "stancer",
    "visa",
    "mastercard",
    "cb",
]

PAYMENT_METHODS_MAPPING = {
    "bank_transfer": "banktransfer",
}

PAYMENT_PAGE = API_HOST.replace("api", "payment")
