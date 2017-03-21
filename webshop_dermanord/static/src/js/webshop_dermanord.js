$(document).ready(function(){
    $('.oe_website_sale').each(function () {
        var oe_website_sale = this;
        $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
            openerp.jsonRpc("/get/product_variant_value", "call", {
                'product_id': $("#current_product_id").data("value"),
                'value_id': $(this).val(),
            }).done(function(data){
                $(".ingredients_description").find("span").html(data);
            });
        });
    });
});
