odoo.define('webshop_dermanord.clarico_variant_accessories', function (require) {

    var concurrency = require('web.concurrency');
    var config = require('web.config');
    var core = require('web.core');
    var publicWidget = require('web.public.widget')
    var utils = require('web.utils');
    var wSaleUtils = require('website_sale.utils');

    var qweb = core.qweb;

    publicWidget.registry.claricoVariantAccessories = publicWidget.Widget.extend({
        selector: '#myCarousel_acce_prod',
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
            this.uniqueId = _.uniqueId('o_carousel_recently_viewed_products_');
            this._onResizeChange = _.debounce(this._addCarousel, 100);
        },
        /**
         * @override
         */
        start: function () {
            this._dp.add(this._fetch()).then(this._render.bind(this));
            $(window).resize(() => {
                this._onResizeChange();
            });
            return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        destroy: function () {
            this._super(...arguments);
            this.$el.addClass('d-none');
            this.$el.find('.slider').html('');
        },

        /**
     * @private
     */
        _fetch: function () {
            console.log("Attempting to fetch variant accessories!!!");
            return this._rpc({
                route: '/shop/products/variant_accessories',
                params: {
                    variant_id: 12,
                },
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
                console.log("Variant accessories have been fetched!!!");
                return res;
            });
        },
    })
});