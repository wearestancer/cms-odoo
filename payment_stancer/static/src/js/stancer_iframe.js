/** @odoo-module */
import PaymentForm from "@payment/js/payment_form";
PaymentForm.include({
  radioInput: document.querySelector('input[data-provider-code="stancer"]'),
  stancerIframe: document.getElementById("stancer-iframe"),
  /**
   * Show or hide the iFrame depending on context
   * @param {boolean} display
   * @returns
   */
  async _displayframe(display = true) {
    const IframeContainer = document.getElementById("stancer-checkout-iframe");
    if (IframeContainer === null) {
      return;
    }
    const PayButton = document.getElementsByName("o_payment_submit_button")[0];
    PayButton.style.display = display ? "none" : "block";
    IframeContainer.style.display = display ? "block" : "none";
  },

  /**
   * Override prepareInlineForm to use direct flow with Stancer payment in case of Iframe.
   *
   * @private
   * @param {number} providerId - The id of the selected payment option's provider.
   * @param {string} providerCode - The code of the selected payment option's provider.
   * @param {number} paymentOptionId - The id of the selected payment option.
   * @param {string} paymentMethodCode - The code of the selected payment method, if any.
   * @param {string} flow - The online payment flow of the selected payment option.
   * @return {void}
   */
  _prepareInlineForm: function (
    providerId,
    providerCode,
    paymentOptionId,
    paymentMethodCode,
    flow
  ) {
    this._super(...arguments);
    if (providerCode !== "stancer") {
      this._displayframe(false);
      return this._super(...arguments);
    }

    this.rpc("/stancer_is_iframe", { provider_id: providerId }).then(
      (iframe) => {
        if (iframe) {
          Object.assign(this.paymentContext, {
            tokenizationRequested: false,
            providerId: providerId,
            paymentMethodId: paymentOptionId,
            flow: "direct",
          });
          this._initiatePaymentFlow(
            providerCode,
            providerId,
            paymentMethodCode,
            "direct"
          );
        }
      }
    );
    return Promise.resolve();
  },

  /**
   * Override
   * Create an Iframe instead of a odoo form, leveraging our payment page.
   * @param {string} providerCode - The code of the provider
   * @param {number} providerId - The id of the provider handling the transaction
   * @param {string} paymentMethodCode the code of the payment method
   * @param {object} processingValues - The processing values of the transaction
   * @returns {Promise}
   */
  _processDirectFlow(
    providerCode,
    providerId,
    paymentMethodCode,
    processingValues
  ) {
    if (providerCode !== "stancer") {
      return this._super(...arguments);
    }
    if (this.radioInput.checked === false) {
      this._displayframe(false);
      return Promise.resolve();
    }
    this._displayframe();
    if (this.stancerIframe.src.includes("about:blank")) {
      return this.rpc("/prepare_stancer_iframe", processingValues).then(
        (rendering_value) => {
          this._stancerHandleIframe(rendering_value);
        }
      );
    }
  },

  /** Link the Iframe to our payment page and add a listener for the return event
   * @param {object} processingValues
   * @returns {void}
   */
  _stancerHandleIframe({ api_url, return_url }) {
    this.stancerIframe.src = api_url;
    window.addEventListener("message", (e) => {
      const data = e.data;

      if (e.origin !== "https://payment.stancer.com") {
        return;
      }

      if (data.status === "finished") {
        this._stancerRedirect(return_url);
        return;
      }
    });
  },

  /**
   * Create a backdrop after the 3ds redirect, making customer wait to be redirected.
   *
   * @param {string} return_url
   * @returns
   */
  _stancerRedirect(return_url) {
    // If we have a backdrop we already are redirected.
    if (document.querySelector(".stancer-backdrop") !== null) {
      return;
    }
    const backdrop = document.createElement("div");
    const redirect_block = document.getElementById("stancer-redirect-iframe");

    backdrop.classList.add("stancer-backdrop");
    document.body.append(backdrop);
    redirect_block.style.display = "block";
    window.location = return_url;
    backdrop.append(redirect_block);
  },
});
