odoo.define('webshop_dermanord.VariantMixin', function (require) {
    'use strict';

    var VariantMixin = require('sale.VariantMixin');

    VariantMixin.events = {
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'change .col-form-label input': '_onChangeButtonAttribute',
        'change .main_product:not(.in_cart) input.js_quantity': 'onChangeAddQuantity',
        'change [data-attribute_exclusions]': 'onChangeVariant'
    }

    /**
     * @see onChangeVariant
     *
     * @private
     * @param {MouseEvent} ev
     * @param {$.Element} $parent
     * @param {Array} combination
     */
    VariantMixin._onChangeCombination = function (ev, $parent, combination) {
        var self = this;
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        let $description = $(':root').find('.product-body');
        $price.text(self._priceToStr(combination.price));
        $default_price.text(self._priceToStr(combination.list_price));

        var isCombinationPossible = true;
        if (!_.isUndefined(combination.is_combination_possible)) {
            isCombinationPossible = combination.is_combination_possible;
        }
        this._toggleDisable($parent, isCombinationPossible);

        if (combination.has_discounted_price) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $optional_price
                .closest('.oe_optional')
                .removeClass('d-none')
                .css('text-decoration', 'line-through');
            $default_price.parent().removeClass('d-none');
        } else {
            $default_price
                .closest('.oe_website_sale')
                .removeClass("discount");
            $optional_price.closest('.oe_optional').addClass('d-none');
            $default_price.parent().addClass('d-none');
        }

        var rootComponentSelectors = [
            'tr.js_product',
            '.oe_website_sale',
            '.o_product_configurator'
        ];

        // update images only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.product_id ||
            !this.last_product_id ||
            combination.product_id !== this.last_product_id) {
            this.last_product_id = combination.product_id;
            self._updateProductImage(
                $parent.closest(rootComponentSelectors.join(', ')),
                combination.display_image,
                combination.product_id,
                combination.product_template_id,
                combination.carousel,
                isCombinationPossible
            );
        }

        $parent
            .find('.product_id')
            .first()
            .val(combination.product_id || 0)
            .trigger('change');

        $parent
            .find('.product_display_name')
            .first()
            .text(combination.display_name);

        $parent
            .find('.js_raw_price')
            .first()
            .text(combination.price)
            .trigger('change');

        $parent
            .find('.col-form-label')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");

        $description
            .find('#nav_tabs_content_description')
            .children()
            .text(combination.description_webshop || "")

        $description
            .find('#nav_tabs_content_use')
            .children()
            .text(combination.description_use || "")

        $description
            .find('#nav_tabs_content_ingredients')
            .children()
            .text(combination.description_ingredients || "" )

        this.handleCustomValues($(ev.target));
    }

    VariantMixin._onChangeColorAttribute = function (ev) {
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    }

    VariantMixin._onChangeButtonAttribute = function (ev) {
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.col-form-label')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    }

    return VariantMixin;

});
