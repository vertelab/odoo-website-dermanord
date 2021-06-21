odoo.define('theme_maria_akerberg.accessories_alternative', function (require) {

    const wSaleUtils = require('website_sale.utils');
    const ajax = require('web.ajax');

    $(document).ready(function(){
        const body = $("body")
        body.on("click", ".accessories_js_add_cart", function(ev){
            const $card = $(ev.currentTarget).closest('.card');
            ajax.jsonRpc("/shop/cart/update_json", 'call', {
                'product_id': $card.find('input[data-product-id]').data('product-id'),
                'add_qty': 1
            })
            .then(function (data) {
                wSaleUtils.updateCartNavBar(data);
            });
        });

        body.on("click", ".alternative_js_add_cart", function(ev){
            const $card = $(ev.currentTarget).closest('.card');
            ajax.jsonRpc("/shop/cart/update_json", 'call', {
                'product_id': $card.find('input[data-product-id]').data('product-id'),
                'add_qty': 1
            })
            .then(function (data) {
                wSaleUtils.updateCartNavBar(data);
            });
        });
    });

})

