/** @odoo-module **/

import PaymentForm from "@payment/js/payment_form";
PaymentForm.include({
  events: Object.assign({}, PaymentForm.prototype.events || {}, {
    "click #o_payment_methods": "_onStancerClick",
  }),

  init() {
    if (
      document.querySelector('input[data-provider-code="stancer"]') === null
    ) {
      return;
    }
    this._super(...arguments);
    this.createIframe();
  },

  stancer_create_iframe() {
    window.addEventListener("message", (e) => {
      const data = e.data;

      if (e.origin !== "https://payment.stancer.com") {
        return;
      }

      if (data.status === "finished" && data.url === null) {
        this.stancer_redirect();
        return;
      }
    });
  },

  stancer_redirect() {
    // If we have a backdrop we already are redirected.
    if (document.querySelector(".stancer-backdrop") !== null) {
      return;
    }
    const backdrop = document.createElement("div");
    const redirect_block = document.getElementById("stancer-redirect-iframe");
    const return_url = "/payment/stancer/return";

    backdrop.classList.add("stancer-backdrop");
    document.body.append(backdrop);
    redirect_block.style.display = "block";
    window.location = return_url;
    backdrop.append(redirect_block);
  },

  async start() {
    return await this._super.apply(this, arguments);
  },

  _onStancerClick(ev) {
    this.init();
  },

  async createIframe() {
    const IframeContainer = document.getElementById("stancer-checkout-iframe");
    const IframeElement = document.getElementById("stancer-iframe");
    const PayButton = document.getElementsByName("o_payment_submit_button")[0];
    const StancerRadio = document.querySelector(
      'input[data-provider-code="stancer"]'
    );

    if (StancerRadio.checked === true) {
      const StancerPaymentId = parseInt(StancerRadio.dataset.providerId, 10);
      const IsIframe = await this.rpc("/stancer_provider_iframe_check", {
        stancer_id: StancerPaymentId,
      });

      if (!IsIframe) {
        return;
      }

      PayButton.style.display = "none";
      IframeContainer.style.display = "block";

      if (IframeElement.src.includes("about:blank")) {
        IframeElement.src = await this.rpc("/prepare_stancer_iframe", {
          stancer_id: StancerPaymentId,
        });
        this.stancer_create_iframe();
      }
    }

    if (StancerRadio.checked === false && IframeContainer !== null) {
      PayButton.style.display = "block";
      IframeContainer.style.display = "none";
    }
  },
});
