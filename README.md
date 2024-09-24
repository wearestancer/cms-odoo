# Stancer Payment Module for Odoo

This official module allows you to accept credit card payments via the Stancer platform directly on Odoo.

## Requirements


## API keys

In order to configure the Odoo module, you need Stancer API keys. You can find your keys in the <q>Developers</q>
tab on your [Stancer account](https://manage.stancer.com).

When creating your account, a private and public key is automatically generated for test mode. Live mode keys will be
created after account validation.

## Supported payment method

The module allows you to make payments by credit card.

Payments are 3D Secure compatible.

## Install

The recommended way of installing this module is through the Odoo marketplace.

- Download the module:
  - via the Odoo Apps Store: search for the Stancer module on the [Odoo Apps Store](https://apps.odoo.com/apps),
    choose the version matching your Odoo version and download it or deploy it on your Odoo.sh instance.
  - via GitHub: go to our [GitHub repository](https://github.com/wearestancer/cms-odoo) choose the branch matching
    your Odoo version, click on the `code` button and choose download as zip.
- Install the module, (a thorough explanation of the installation process can be found
  [here](https://www.cybrosys.com/blog/how-to-install-custom-modules-in-odoo)).
- Open **Website > Configuration > Payment provider > Stancer**
- Enter your Public and Private keys.
- Choose the enabled state.
- Don't forget to save your changes.
- After that the module is ready to be used as a payment method on your website.

## License

MIT license.

For more information, see the LICENSE file.
