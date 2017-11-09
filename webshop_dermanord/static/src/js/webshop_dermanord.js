var website = openerp.website;
website.add_template_file('/webshop_dermanord/static/src/xml/product.xml');
var current_page = 2;
var page_count = 0;

$(document).ready(function(){

    $("input[data-toggle='tooltip']").click(function() {
        $("input[data-toggle='tooltip']").tooltip('hide');
        $(this).tooltip();
    });

    $(".show_more_facet").click(function(){
        $(this).addClass("hidden");
        $(".hide_more_facet").removeClass("hidden");
        $(".facet_container").removeClass("hidden-xs");
    });

    $(".hide_more_facet").click(function(){
        $(this).addClass("hidden");
        $(".show_more_facet").removeClass("hidden");
        $(".facet_container").addClass("hidden-xs");
    });

    $(".oe_dn_list").on('click', 'a.js_add_cart_json', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.closest(".css_quantity").find("input");
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
        $input.val(quantity > min ? (quantity < max ? quantity : max) : min);
        return false;
    });

    $('.oe_shop_list .a-submit, #comment .a-submit').off('click').on('click', function () {
        $(this).closest('form').submit();
    });

    $(".like").click(function(){
        if($(this).is(":checked")) {
            $(this).closest(".checkbox").find(".unlike").removeAttr('checked');
        }
    });

    $(".unlike").click(function(){
        if($(this).is(":checked")) {
            $(this).closest(".checkbox").find(".like").removeAttr('checked');
        }
    });



    function update_product_image(event_source, product_id) {
        var $img = $(event_source).closest('tr.js_product, .oe_website_sale').find('span[data-oe-model^="product."][data-oe-type="image"] img:first, img.product_detail_img');
        var $img_thumb = $(event_source).closest('tr.js_product, .oe_website_sale').find("#image_nav").find("li:first").find("img");
        openerp.jsonRpc("/get/product_variant_data", "call", {
            'product_id': product_id,
        }).done(function(data){
            if (data['image_id'] != null) {
                $img.attr("src", "/imagefield/base_multi_image.image/image_main/" + data['image_id'] + "/ref/website_sale_product_gallery.img_product_detail");
                $img_thumb.attr("src", "/imagefield/base_multi_image.image/image_main/" + data['image_id'] + "/ref/website_sale_product_gallery.img_product_thumbnail");
            }
            $(".ingredients_description").find(".text-muted").html(data['ingredients']);
            $(".default_code").html(data['default_code']);
            $(".use_desc").html(data['use_desc']);
            $(".reseller_desc").html(data['reseller_desc']);
        });
        $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
            .data('oe-model', 'product.product').data('oe-id', product_id);
    }

    $('.oe_website_sale').each(function () {
        var oe_website_sale = this;

        var $shippingDifferent = $("select[name='shipping_id']", oe_website_sale);
        $shippingDifferent.change(function (event) {
            var value = +$shippingDifferent.val();
            var data = $shippingDifferent.find("option:selected").data();
            $('.row.shipping-address').addClass('hidden');
            $('#shipping_addr_' + value).removeClass('hidden');
        });
        
        var $invoicingDifferent = $("select[name='invoicing_id']", oe_website_sale);
        $invoicingDifferent.change(function (event) {
            var value = +$invoicingDifferent.val();
            var data = $invoicingDifferent.find("option:selected").data();
            $('.row.invoicing-address').addClass('hidden');
            $('#invoicing_addr_' + value).removeClass('hidden');
        });

        $(oe_website_sale).on("change", 'input[name="add_qty"]', function (event) {
            product_ids = [];
            var product_dom = $(".js_product .js_add_cart_variants[data-attribute_value_ids]").last();
            product_dom.data("attribute_value_ids").forEach(function(entry) {
                product_ids.push(entry[0]);});
            var qty = $(event.target).closest('form').find('input[name="add_qty"]').val();

            openerp.jsonRpc("/shop/get_unit_price", 'call', {'product_ids': product_ids,'add_qty': parseInt(qty)})
            .then(function (data) {
                var current = product_dom.data("attribute_value_ids");
                for(var j=0; j < current.length; j++){
                    current[j][2] = data[current[j][0]];
                }
                product_dom.attr("data-attribute_value_ids", JSON.stringify(current)).trigger("change");
            });
        });

        // change for css
        $(oe_website_sale).on('mouseup touchend', '.js_publish', function (ev) {
            $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
        });

        $(oe_website_sale).find(".oe_cart input.js_quantity").on("change", function () {
            var $input = $(this);
            if ($input.data('update_change')) {
                return;
            }
            var value = parseInt($input.val(), 10);
            var $dom = $(this).closest('tr');
            var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
            var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            var line_id = parseInt($input.data('line-id'),10);
            var product_id = parseInt($input.data('product-id'),10);
            var product_ids = [product_id];
            $dom_optional.each(function(){
                product_ids.push($(this).find('span[data-product-id]').data('product-id'));
            });
            if (isNaN(value)) value = 0;
            $input.data('update_change', true);
            openerp.jsonRpc("/shop/get_unit_price", 'call', {
                'product_ids': product_ids,
                'add_qty': value,
                'use_order_pricelist': true,
                'line_id': line_id})
            .then(function (res) {
                //basic case
                $dom.find('span.oe_currency_value').last().text(price_to_str(res[product_id]));
                $dom.find('.text-danger').toggle(res[product_id]<default_price && (default_price-res[product_id] > default_price/100));
                //optional case
                $dom_optional.each(function(){
                    var id = $(this).find('span[data-product-id]').data('product-id');
                    var price = parseFloat($(this).find(".text-danger > span.oe_currency_value").text());
                    $(this).find("span.oe_currency_value").last().text(price_to_str(res[id]));
                    $(this).find('.text-danger').toggle(res[id]<price && (price-res[id]>price/100));
                });
                openerp.jsonRpc("/shop/cart/update_json", 'call', {
                'line_id': line_id,
                'product_id': parseInt($input.data('product-id'),10),
                'set_qty': value})
                .then(function (data) {
                    $input.data('update_change', false);
                    if (value !== parseInt($input.val(), 10)) {
                        $input.trigger('change');
                        return;
                    }
                    if (!data.quantity) {
                        location.reload(true);
                        return;
                    }
                    var $q = $(".my_cart_quantity");
                    $q.parent().parent().removeClass("hidden", !data.quantity);
                    $q.html(data.cart_quantity).hide().fadeIn(600);

                    $input.val(data.quantity);
                    $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                    $("#cart_total").replaceWith(data['website_sale.total']);
                });
            });
        });

        // hack to add and rome from cart with json
        $(oe_website_sale).on('click', 'a.js_add_cart_json', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.parent().parent().find("input");
            var min = parseFloat($input.data("min") || 0);
            var max = parseFloat($input.data("max") || Infinity);
            var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
            $input.val(quantity > min ? (quantity < max ? quantity : max) : min);
            //~ $('input[name="'+$input.attr("name")+'"]').val(quantity > min ? (quantity < max ? quantity : max) : min);
            //~ $input.change();
            return false;
        });

        $('.oe_website_sale .a-submit, #comment .a-submit').off('click').on('click', function () {
            $(this).closest('form').submit();
        });
        $('form.js_attributes input, form.js_attributes select', oe_website_sale).on('change', function () {
            $(this).closest("form").submit();
        });

        // change price when they are variants
        $('form.js_add_cart_json label', oe_website_sale).on('mouseup touchend', function (ev) {
            var $label = $(this);
            var $price = $label.parents("form:first").find(".oe_price .oe_currency_value");
            if (!$price.data("price")) {
                $price.data("price", parseFloat($price.text()));
            }
            var value = $price.data("price") + parseFloat($label.find(".badge span").text() || 0);
            var dec = value % 1;
            $price.html(value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") ));
        });
        // hightlight selected color
        $('.css_attribute_color input', oe_website_sale).on('change', function (ev) {
            $('.css_attribute_color').removeClass("active");
            $('.css_attribute_color:has(input:checked)').addClass("active");
        });

        // Copy from core.js that is not available in front end.
        function intersperse(str, indices, separator) {
            separator = separator || '';
            var result = [], last = str.length;

            for(var i=0; i<indices.length; ++i) {
                var section = indices[i];
                if (section === -1 || last <= 0) { break; }
                else if(section === 0 && i === 0) { break; }
                else if (section === 0) { section = indices[--i]; }
                result.push(str.substring(last-section, last));
                last -= section;
            }
            var s = str.substring(0, last);
            if (s) { result.push(s); }
            return result.reverse().join(separator);
        }
        function insert_thousand_seps(num) {
            var l10n = openerp._t.database.parameters;
            var negative = num[0] === '-';
            num = (negative ? num.slice(1) : num);
            // retro-compatibilit: if no website_id and so l10n.grouping = []
            var grouping = l10n.grouping instanceof Array ? l10n.grouping : JSON.parse(l10n.grouping);
            return (negative ? '-' : '') + intersperse(
                num, grouping, l10n.thousands_sep);
        }

        function price_to_str(price) {
            var l10n = openerp._t.database.parameters;
            var precision = 2;
            if ($(".decimal_precision").length) {
                var dec_precision = $(".decimal_precision").first().data('precision');
                //Math.log10 is not implemented in phantomJS
                dec_precision = Math.round(Math.log(1/parseFloat(dec_precision))/Math.log(10));
                if (!isNaN(dec_precision)) {
                    precision = dec_precision;
                }
            }
            var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
            formatted[0] = insert_thousand_seps(formatted[0]);
            return formatted.join(l10n.decimal_point);
        }

        $(oe_website_sale).on('change', 'input.js_product_change', function (ev) {
            var $parent = $(this).closest('.js_product');
            $parent.find(".oe_default_price:first .oe_currency_value").html( price_to_str(+$(this).data('lst_price')) );
            $parent.find(".oe_price:first .oe_currency_value").html(price_to_str(+$(this).data('price')) );
            update_product_image(this, +$(this).val());
        });

        $(oe_website_sale).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
            var $ul = $(ev.target).closest('.js_add_cart_variants');
            var $parent = $ul.closest('.js_product');
            var $product_id = $parent.find('input.product_id').first();
            var $price = $parent.find(".oe_price:first .oe_currency_value");
            var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
            var $recommended_price = $parent.find(".oe_recommended_price:first .oe_currency_value");
            var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
            var variant_ids = $ul.data("attribute_value_ids");
            var values = [];
            $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
                values.push(+$(this).val());
            });

            $parent.find("label").removeClass("text-muted css_not_available");

            var product_id = false;
            for (var k in variant_ids) {
                console.log(k);
                if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                    openerp.website.ready().then(function() {
                        $price.html(price_to_str(variant_ids[k][2]));
                        $default_price.html(price_to_str(variant_ids[k][3]));
                        $recommended_price.html(price_to_str(variant_ids[k][4]));
                        $('#sale_start_info').removeClass('hidden')
                    });
                    if (variant_ids[k][3]-variant_ids[k][2]>0.2) {
                        $default_price.closest('.oe_website_sale').addClass("discount");
                        $optional_price.closest('.oe_optional').show().css('text-decoration', 'line-through');
                    } else {
                        $default_price.closest('.oe_website_sale').removeClass("discount");
                        $optional_price.closest('.oe_optional').hide();
                    }
                    product_id = variant_ids[k][0];
                    break;
                }
                 // sale_ok / sale_start hide add-button and maybe view information about sale start
                //~ if (sale_ok[k][2] == 'False') {
                    //~ $('#add_to_cart').addClass('hidden');
                    //~ if (sale_ok[k][3] != '') {
                        //~ $('#sale_start_info').removeClass('hidden');
                        //~ $('#sale_start').html(sale_ok[k][3]);
                    //~ }
                //~ }
            }

            if (product_id) {
                update_product_image(this, product_id);
            }

            $parent.find("input.js_variant_change:radio, select.js_variant_change").each(function () {
                var $input = $(this);
                var id = +$input.val();
                var values = [id];

                $parent.find("ul:not(:has(input.js_variant_change[value='" + id + "'])) input.js_variant_change:checked, select").each(function () {
                    values.push(+$(this).val());
                });

                for (var k in variant_ids) {
                    if (!_.difference(values, variant_ids[k][1]).length) {
                        return;
                    }
                }
                $input.closest("label").addClass("css_not_available");
                $input.find("option[value='" + id + "']").addClass("css_not_available");
            });

            if (product_id) {
                $parent.removeClass("css_not_available");
                $product_id.val(product_id);
                $parent.find(".js_check_product").removeAttr("disabled");
            } else {
                $parent.addClass("css_not_available");
                $product_id.val(0);
                $parent.find(".js_check_product").attr("disabled", "disabled");
            }
        });

        $('div.js_product', oe_website_sale).each(function () {
            $('input.js_product_change', this).first().trigger('change');
        });

        $('.js_add_cart_variants', oe_website_sale).each(function () {
            $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
        });

        $(oe_website_sale).on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $(oe_website_sale).find("select[name='country_id']").change();

        //~ $(oe_website_sale).on('change', "select[name='shipping_country_id']", function () {
            //~ var $select = $("select[name='shipping_state_id']");
            //~ $select.find("option:not(:first)").hide();
            //~ var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            //~ $select.parent().toggle(nb>1);
        //~ });
        //~ $(oe_website_sale).find("select[name='shipping_country_id']").change();
    });

    $(window).scroll(function() {
        if ($(window).scrollTop() + $(window).height() == $(document).height()) {
            if ($("#wrap").hasClass("autoload_grid")) {
                load_products_grid(current_page);
            }
            if ($("#wrap").hasClass("autoload_list")) {
                load_products_list(current_page);
            }
        }
    });
});

function load_products_grid(page){
    openerp.jsonRpc("/dn_shop_json_grid", "call", {
        'page': current_page.toString(),
    }).done(function(data){
        page_count = data['page_count'];
        if (page_count >= current_page) {
            var products_content = '';
            $.each(data['products'], function(key, info) {
                var content = openerp.qweb.render('products_item_grid', {
                    'url': data['url'],
                    'product_id': key,
                    'product_href': data['products'][key]['product_href'],
                    'product_name': data['products'][key]['product_name'],
                    'product_img_src': data['products'][key]['product_img_src'],
                    'price': data['products'][key]['price'],
                    'price_tax': data['products'][key]['price_tax'],
                    'list_price_tax': data['products'][key]['list_price_tax'],
                    'currency': data['products'][key]['currency'],
                    'rounding': data['products'][key]['rounding'],
                    'is_reseller': data['products'][key]['is_reseller'],
                    'default_code': data['products'][key]['default_code'],
                    'description_sale': data['products'][key]['description_sale'],
                    'product_variant_ids': data['products'][key]['product_variant_ids']
                });
                products_content += content;
            });
            $(".oe_website_sale").find('.row').append(products_content);
            current_page ++;
        }
    });
}

function load_products_list(page){
    openerp.jsonRpc("/dn_shop_json_list", "call", {
        'page': current_page.toString(),
    }).done(function(data){
        page_count = data['page_count'];
        if (page_count >= current_page) {
            var products_content = '';
            $.each(data['products'], function(key, info) {
                var content = openerp.qweb.render('products_item_list', {
                    'url': data['url'],
                    'product_id': data['products'][key]['variant_id'],
                    'product_href': data['products'][key]['product_href'],
                    'product_name': data['products'][key]['product_name'],
                    'attribute_value_ids': data['products'][key]['attribute_value_ids'],
                    'price': data['products'][key]['price'],
                    'currency': data['products'][key]['currency'],
                    'rounding': data['products'][key]['rounding'],
                    'is_reseller': data['products'][key]['is_reseller'],
                    'default_code': data['products'][key]['default_code']
                });
                products_content += content;
            });
            $(".oe_website_sale").find('tbody').append(products_content);
            current_page ++;
        }
    });
}

function webshop_restore_filter() {
    $("#dn_filter_modal").find(".modal-body").find("input[type=checkbox]").each(
        function() {
            if($(this).is(":checked")) {
                $(this).removeAttr('checked');
            }
        }
    );
    $("#desktop_product_navigator_filter").find(".panel-group").find("input[type=checkbox]").each(
        function() {
            if($(this).is(":checked")) {
                $(this).removeAttr('checked');
            }
        }
    );
}

$(".desktop_angle").click(function(){
    if($(this).hasClass("fa-angle-down")) {
        $(this).removeClass("fa-angle-down");
        $(this).addClass("fa-angle-up");
    }
    else {
        $(this).removeClass("fa-angle-up");
        $(this).addClass("fa-angle-down");
    }
});
