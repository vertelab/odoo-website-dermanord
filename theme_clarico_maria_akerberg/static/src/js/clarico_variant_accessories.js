odoo.define('webshop_dermanord.clarico_variant_accessories', function (require) {

    var concurrency = require('web.concurrency');
    var config = require('web.config');
    var core = require('web.core');
    var publicWidget = require('web.public.widget')
    var utils = require('web.utils');
    var wSaleUtils = require('website_sale.utils');
    var ajax = require('web.ajax');
    var VariantMixin = require('sale.VariantMixin');
    var qweb = core.qweb;


    VariantMixin.events = {
        'change .col-form-label input': (e) => {
            let test = publicWidget.registry.claricoVariantAccessories;
            test.prototype._getVariationInfo(e);
        },
    }

    publicWidget.registry.claricoVariantAccessories = publicWidget.Widget.extend({
        selector: '.accessory_product_main',
        xmlDependencies: ['/theme_clarico_maria_akerberg/static/src/xml/clarico_variant_accessories.xml'],
        disabledInEditableMode: false,
        read_events: {
            'click .js_add_cart': '_onAddToCart',
            'click .js_remove': '_onRemove',
        },

        /**
        * @constructor
        */
        init: function () {
            this._super.apply(this, arguments);
            this._dp = new concurrency.DropPrevious();
            this.uniqueId = _.uniqueId('o_carousel_variant_product_');
            this._onResizeChange = _.debounce(this._addCarousel, 100);
        },
        /**
         * @override
         */
        start: function (id) {
            if (id === undefined) {
                id = $('#product_details').find('.product_id').attr('value')
            }
            this._dp.add(this._fetch(id)).then(this._render.bind(this));
            $(window).resize(() => {
                this._onResizeChange();
            });
            return this._super.apply(this, arguments);
        },
        render: function (id) {
            this._fetch(id).then(this._render.bind(this));
        },
        /**
        * Will return the list of selected product.template.attribute.value ids
        * For the modal, the "main product"'s attribute values are stored in the
        * "unchanged_value_ids" data
        *
        * @param {$.Element} $container the container to look into
        */
        getSelectedVariantValues: function ($container) {
            var values = [];
            var unchangedValues = $container
                .find('div.oe_unchanged_value_ids')
                .data('unchanged_value_ids') || [];

            var variantsValuesSelectors = [
                'input.js_variant_change:checked',
                'select.js_variant_change'
            ];
            _.each($container.find(variantsValuesSelectors.join(', ')), function (el) {
                values.push(+$(el).val());
            });

            return values.concat(unchangedValues);
        },

        /**
        * @private
        */
        _fetch: function (variant_id = false) {
            if (variant_id) {
                return ajax.jsonRpc(this._getUri('/shop/products/variant_accessories'), 'call', {
                    "variant_id": variant_id,
                }).then(res => {
                    var products = res['products'];

                    // In edit mode, if the current visitor has no recently viewed
                    // products, use demo data.
                    if (this.editableMode && (!products || !products.length)) {
                        return {
                            'products': [{
                                id: 0,
                                website_url: '#',
                                display_name: 'Product 1',
                                price: '$ <span class="oe_currency_value">750.00</span>',
                            }, {
                                id: 0,
                                website_url: '#',
                                display_name: 'Product 2',
                                price: '$ <span class="oe_currency_value">750.00</span>',
                            }, {
                                id: 0,
                                website_url: '#',
                                display_name: 'Product 3',
                                price: '$ <span class="oe_currency_value">750.00</span>',
                            }, {
                                id: 0,
                                website_url: '#',
                                display_name: 'Product 4',
                                price: '$ <span class="oe_currency_value">750.00</span>',
                            }],
                        };
                    }
                    return res;
                });
            }
        },
        /**
         * @private
         */
        _render: function (res) {
            var products = res['products'];
            var mobileProducts = [], webProducts = [], productsTemp = [];
            _.each(products, function (product) {
                if (productsTemp.length === 4) {
                    webProducts.push(productsTemp);
                    productsTemp = [];
                }
                productsTemp.push(product);
                mobileProducts.push([product]);
            });
            if (productsTemp.length) {
                webProducts.push(productsTemp);
            }

            this.mobileCarousel = $(qweb.render('website_sale.claricoVariantAccessories', {
                uniqueId: this.uniqueId,
                productFrame: 1,
                productsGroups: mobileProducts,
            }));
            this.webCarousel = $(qweb.render('website_sale.claricoVariantAccessories', {
                uniqueId: this.uniqueId,
                productFrame: 2,
                productsGroups: webProducts,
            }));
            this._addCarousel();
        },
        /**
         * @private
         */
        _update: function () {
            console.log("Hello from variants update!");
            $(":root").find('.col-form-label input');
        },
        /**
         * Add the right carousel depending on screen size.
         * @private
         */
        _addCarousel: function () {
            var carousel = config.device.size_class <= config.device.SIZES.SM ? this.mobileCarousel : this.webCarousel;
            $('#myCarousel_acce_prod').find('.owl-carousel').html(carousel).css('display', ''); // Removing display is kept for compatibility (it was hidden before)
        },
        /**
        * Extension point for website_sale
        *
        * @private
        * @param {string} uri The uri to adapt
        */
        _getUri: function (uri) {
            return uri;
        },
        /**
        * Extracted to a method to be extendable by other modules
        *
        * @param {$.Element} $parent
        */
        _getProductId: function ($parent) {
            return parseInt($parent.find('.product_id').val());
        },

        /**
        * Will disable attribute value's inputs based on combination exclusions
        * and will disable the "add" button if the selected combination
        * is not available
        *
        * This will check both the exclusions within the product itself and
        * the exclusions coming from the parent product (meaning that this product
        * is an option of the parent product)
        *
        * It will also check that the selected combination does not exactly
        * match a manually archived product
        *
        * @private
        * @param {$.Element} $parent the parent container to apply exclusions
        * @param {Array} combination the selected combination of product attribute values
        */
        _checkExclusions: function ($parent, combination) {
            var self = this;
            var combinationData = $parent
                .find('ul[data-attribute_exclusions]')
                .data('attribute_exclusions');

            $parent
                .find('option, input, label')
                .removeClass('css_not_available')
                .prop('disabled', false)
                .attr('title', function () { return $(this).data('value_name') || ''; })
                .data('excluded-by', '');

            // exclusion rules: array of ptav
            // for each of them, contains array with the other ptav they exclude
            if (combinationData.exclusions) {
                // browse all the currently selected attributes
                _.each(combination, function (current_ptav) {
                    if (combinationData.exclusions.hasOwnProperty(current_ptav)) {
                        // for each exclusion of the current attribute:
                        _.each(combinationData.exclusions[current_ptav], function (excluded_ptav) {
                            // disable the excluded input (even when not already selected)
                            // to give a visual feedback before click
                            self._disableInput(
                                $parent,
                                excluded_ptav,
                                current_ptav,
                                combinationData.mapped_attribute_names
                            );
                        });
                    }
                });
            }

            // parent exclusions (tell which attributes are excluded from parent)
            _.each(combinationData.parent_exclusions, function (exclusions, excluded_by) {
                // check that the selected combination is in the parent exclusions
                _.each(exclusions, function (ptav) {

                    // disable the excluded input (even when not already selected)
                    // to give a visual feedback before click
                    self._disableInput(
                        $parent,
                        ptav,
                        excluded_by,
                        combinationData.mapped_attribute_names,
                        combinationData.parent_product_name
                    );
                });
            });
        },
        /**
        *
        * @private
        * @param {Event} e
        * @returns {Deferred}
        */
        _getVariationInfo: function (e) {
            console.log(e)
            var self = this;

            if ($(e.target).hasClass('variant_custom_value')) {
                return Promise.resolve();
            }

            var $parent = $(e.target).closest('.js_product');
            var qty = $parent.find('input[name="add_qty"]').val();
            var combination = this.getSelectedVariantValues($parent);
            var parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
            var productTemplateId = parseInt($parent.find('.product_template_id').val());

            self._checkExclusions($parent, combination);

            return ajax.jsonRpc(this._getUri('/sale/get_combination_info'), 'call', {
                'product_template_id': productTemplateId,
                'product_id': this._getProductId($parent),
                'combination': combination,
                'add_qty': parseInt(qty),
                'pricelist_id': this.pricelistId || false,
                'parent_combination': parentCombination,
            }).then(function (combinationData) {
                let test = publicWidget.registry.claricoVariantAccessories;
                test.prototype.render(combinationData.product_id)
            });
        },
    })
});
