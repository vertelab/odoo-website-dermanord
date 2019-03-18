var website = openerp.website;
website.add_template_file('/webshop_dermanord/static/src/xml/product.xml');
var current_page = 0;
var page_count = 0;
var lang = $("html").attr("lang");
var dn_loading_products = false;

$("select.attr_sel").on('change', function() {
    var $self = $(this);
    var sel_lst = [];
    var $these_sel = $self.closest("ul").find(("select.attr_sel"));
    $.each($these_sel, function() {
        sel_lst.push($(this).val());
    });
    // validate attribute_value exists on variant
    //~ openerp.jsonRpc("/validate_attibute_value", "call", {
        //~ 'product_id': $self.attr("name").split("-")[1],
        //~ 'attribute_value_id': $self.val(),
        //~ 'attribute_value_list': sel_lst
    //~ }).done(function(data){
        //~ sel_lst = data;
    //~ });
    $.each($("option"), function() {
        if ($.inArray($(this).attr("value"), sel_lst) !== -1) {
            $(this).attr("selected", "selected");
            activate_section($self.val(), sel_lst);
        }
        else {
            $(this).removeAttr("selected");
        }
    });
    function activate_section(sel_val, lst) {
        var found = false;
        var ls = lst.sort(function(a, b){return a - b});
        $.each($("section.oe_website_sale"), function() {
            if ($(this).attr("id") == ("section_" + ls.join("_"))) {
                $(this).removeClass("hidden");
                found = true;
            }
            else {
                $(this).addClass("hidden");
            }
        });
        if (!found) {
            $.each($("section.oe_website_sale"), function() {
                if ($(this).attr("id") == ("section_" + sel_val)) {
                    $(this).removeClass("hidden");
                    found = true;
                }
                else if (!found && (~$(this).attr("id").indexOf("section_" + sel_val) || ~$(this).attr("id").indexOf("section_") && ~$(this).attr("id").indexOf("_" + sel_val))) {
                    var $this_select = $(this);
                    $this_select.removeClass("hidden");
                    var section_id_lst = $this_select.attr("id");
                    var attr_lst = section_id_lst.split("section_")[1].split("_");
                    $.each($this_select.find("option"), function() {
                        $att_val = $(this).val();
                        if ($.inArray($att_val, attr_lst) !== -1) {
                            $(this).attr("selected", "selected");
                        }
                        else {
                            $(this).removeAttr("selected");
                        }
                    });
                    found = true;
                }
                else {
                    $(this).addClass("hidden");
                }
            });
        }
    }
});

function submit_facet($facet) {
    //~ $facet.closest("h5").find("input[type='checkbox']").attr("checked", "checked");
    $facet.prev().attr("checked", "checked");
    $facet.closest("form").submit();
}

function onclick_submit($element) {
    $.each($element.closest("div.panel").find(".onrs_style"), function() {
        $(this).prev().attr("checked", false);
    });
    $element.prev().attr("checked", true);
    //~ $element.closest("form").append('<input name="post_form" value="ok" type="hidden"/>');
    $element.closest("form").submit();
}

function show_popover(trigger){
    trigger.popover({
        container: 'body',
        html: true,
        content: function () {
            var clone = $(trigger.data('popover-content')).clone(true).removeClass('hide');
            return clone;
        }
    }).click(function(e) {
        e.preventDefault();
    });
};

function setCartPriceQuantity(price, quantity, price_float) {
    var ts = $(".my_cart_total").data('thousands_sep');
    var dp = $(".my_cart_total").data('decimal_point');
    var x = price.split('.');
    var x1 = x[0];
    var x2 = x.length > 1 ? dp + x[1] : '';
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x1)) {
        x1 = x1.replace(rgx, '$1' + ts + '$2');
    }
    $(".my_cart_total > .oe_currency_value").text(x1 + x2);
    $(".my_cart_quantity").text('(' + quantity + ')');
    $(".my_cart_quantity").data("price", price_float);
}

$(document).ready(function(){

    $("input.category_checkbox").change(function() {
        category_checkbox_onchange($(this));
    });

    $(".onclick_category").click(function() {
        var $input = $(this).prev();
        $.each($input.closest("div.category_filter").find("input[class='category_checkbox']"), function() {
            $(this).attr("checked", false);
        });
        $input.attr("checked", true);
        category_checkbox_onchange($input);
        check_in_check_out_parent();
        $input.closest("form").submit();
    });

    function category_checkbox_onchange($e) {
        var $self = $e;
        var checked = $self.is(":checked");
        var categ_id = $self.data("category");
        if (categ_id != "") {
            $.each($self.closest("div.panel").find("div#" + categ_id + " input[type='checkbox']"), function() {
                if (checked) {
                    $(this).attr("checked", true);
                }
                else {
                    $(this).attr("checked", false);
                }
            });
            activate_facet();
        }
    }

    $("input.heading_checkbox").change(function() {
        var $self = $(this);
        var checked = $self.is(":checked");
        var facet_id = $self.next().attr("href").replace("#", "");
        if (facet_id != "") {
            $.each($self.closest("div.panel").find("div#" + facet_id + " input[type='checkbox']"), function() {
                if (checked)
                    $(this).attr("checked", "checked");
                else
                    $(this).removeAttr("checked", "checked");
            });
            activate_facet();
        }
    });

    $("input.facet_heading_checkbox").change(function() {
        var $self = $(this);
        var checked = $self.is(":checked");
        var div_id = $self.closest("h4").find("a[data-toggle='collapse']").attr("href");
        $.each($self.closest("div.panel").find(div_id).find(".facet_checkbox"), function() {
            if (checked)
                $(this).attr("checked", "checked");
            else
                $(this).removeAttr("checked", "checked");
        });
    });

    function category_heading_parents() {
        $.each($("div.panel-heading.category_heading_parents"), function() {
            var $self = $(this);
            var $h4 = $self.find("h4.panel-title.parent_category_panel_title");
            var input_checked_count = 0;
            if ($self.find("input.category_checkbox").first().is(":checked")) {
                input_checked_count += 1;
            }
            var div_categories_id = $self.find("input.category_checkbox").data("category");
            var $submenu_div = $self.closest("div.panel.panel-default").find("div#" + div_categories_id)
            var $all_child_checkbox = $submenu_div.find("input.category_checkbox");
            $.each($all_child_checkbox, function() {
                if ($(this).is(":checked")) {
                   input_checked_count += 1;
                   $(this).closest("div.panel-collapse").addClass("in");
                }
            });
            if (input_checked_count != 0) {
                $h4.append('<span class="filter_match">' + input_checked_count + '</span>');
                $submenu_div.addClass("in");
            }
        });
    }

    function facet_heading_parents() {
        $.each($("div.panel-heading.facet_panel_heading"), function() {
            var $self = $(this);
            var $h4 = $self.find("h4.panel-title");
            var input_checked_count = 0;
            var div_facet_id = $h4.find("a").attr("href");
            var all_child_checkbox = $self.closest("div.panel.panel-default").find(div_facet_id).find("input.facet_checkbox");
            $.each(all_child_checkbox, function() {
                if ($(this).is(":checked")) {
                    input_checked_count += 1;
                }
            });
            if (input_checked_count != 0) {
                $h4.append(' <span class="filter_match">' + input_checked_count + '</span>');
            }
        });
    }

    function activate_facet() {
        var $desktop = $("div#desktop_product_navigator");
        var $mobile = $("div#webshop_dermanord_mobile_filter_modal");
        do_update($desktop);
        do_update($mobile);
        function do_update($e) {
            var all_active_categ_ids = [];
            $.each($e.find("input.category_checkbox"), function() {
                var $self = $(this);
                var categ_id = parseInt($self.data("parent_category"));
                if ($self.is(":checked")) {
                    if ($.inArray(categ_id, all_active_categ_ids) === -1) {
                        all_active_categ_ids.push(categ_id);
                    }
                }
            });
            $.each($e.find("div.facet_panel_heading"), function() {
                var $self = $(this);
                var $c_list = $self.data("categories");
                if ($c_list !== undefined) {
                    $.each($c_list, function(key, val) {
                        if ($.inArray(val, all_active_categ_ids) !== -1) {
                            $self.removeClass("hidden");
                            $self.closest(".panel").find("div#" + $self.data("mobile") + "_facet_" + $self.data("facet")).removeClass("hidden");
                            return false;
                        }
                        else {
                            $self.addClass("hidden");
                            var $facet = $self.closest(".panel").find("div#" + $self.data("mobile") + "_facet_" + $self.data("facet"));
                            $facet.addClass("hidden");
                            $facet.find("input[type='checkbox']").removeAttr("checked");
                        }
                    });
                }
            });
        }
    }

    function mobile_filter_count() {
        var count = 0;
        $.each($("div#webshop_dermanord_mobile_filter_modal").find("span.filter_match"), function() {
            count += parseInt($(this).text());
        });
        if (count != 0) {
            $("span#mobile_filter_match").text(count);
            $("span#mobile_filter_match").removeClass("hidden");
        }
        else {
            $("span#mobile_filter_match").addClass("hidden");
        }
    }

    category_heading_parents();
    facet_heading_parents();
    activate_facet();
    mobile_filter_count();
    check_in_check_out_parent();

    openerp.jsonRpc("/website_sale_update_cart", "call", {
    }).done(function(data){
        $(".my_cart_total").data('thousands_sep', data['thousands_sep']);
        $(".my_cart_total").data('decimal_point', data['decimal_point']);
        $(".my_cart_currency").text('' + data['currency']);
        setCartPriceQuantity(data['amount_untaxed'], data['cart_quantity'], data['amount_float']);
    });

    $("input[data-toggle='tooltip']").click(function() {
        $("input[data-toggle='tooltip']").tooltip('hide');
        $(this).tooltip();
    });

    $('[data-toggle="tooltip"]').tooltip();

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

    // There was probably some reason we disabled this. Write it down next time.
    var product_price_form = $('form.js_add_cart_variants');

    $('.oe_website_sale').each(function () {
        var oe_website_sale = this;

        var $shippingDifferent = $("select[name='shipping_id']", oe_website_sale);
        $shippingDifferent.change(function (event) {
            var value = +$shippingDifferent.val();
            var data = $shippingDifferent.find("option:selected").data();
            $('.shipping-address').addClass('hidden');
            $('#shipping_addr_' + value).removeClass('hidden');
        });

        var $invoicingDifferent = $("select[name='invoicing_id']", oe_website_sale);
        $invoicingDifferent.change(function (event) {
            var value = +$invoicingDifferent.val();
            var data = $invoicingDifferent.find("option:selected").data();
            $('.invoicing-address').addClass('hidden');
            $('#invoicing_addr_' + value).removeClass('hidden');
        });

        $(oe_website_sale).on("change", 'input[name="add_qty"]', function (event) {
            product_ids = [];
            var $product_dom = $(this).closest("form");
            //~ $product_dom.data("attribute_value_ids").each(function(entry) {
                //~ product_ids.push(entry[0]);
            //~ });
            product_ids.push($product_dom.data("attribute_value_ids"));
            var qty = $product_dom.find('input[name="add_qty"]').val();
            var $input = $product_dom.find('input[name="add_qty"]');

            // Make sure quantity is not > 5 if it's an educational purchase
            if ($input.data('edu-purchase') == '1') {
                if (qty > 5) {
                    qty = 5;
                    $input.val(parseInt(qty));
                }
            }
            
            // TODO: Next row causes type 200 error to be thrown. [product_ids[0]] or product_ids[0] both cause errors.
            // product_ids[0] throws error on product list page.
            // [product_ids[0]] throws error on product page.
            openerp.jsonRpc("/shop/get_unit_price", 'call', {'product_ids': product_ids[0], 'add_qty': parseInt(qty)})
            .then(function (data) {
                var current = $product_dom.data("attribute_value_ids");
                for(var j=0; j < current.length; j++){
                    current[j][2] = data[current[j][0]];
                }
                $product_dom.attr("data-attribute_value_ids", JSON.stringify(current)).trigger("change");
            });
        });

        // change for css
        $(oe_website_sale).on('mouseup touchend', '.js_publish', function (ev) {
            $(ev.currentTarget).parents(".thumbnail").toggleClass("disabled");
        });

        $(oe_website_sale).find(".oe_cart input.js_quantity").live("change", function () {
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
            if ($input.data('edu-purchase') == '1') {
                if (value > 5) {
                    value = 5;
                    $input.val(value);
                } 
            }
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
                    var $q = $(".my_cart_quantity");
                    if (value !== parseInt($input.val(), 10)) {
                        $input.trigger('change');
                        return;
                    }

                    if (data.cart_quantity === undefined) {data.cart_quantity=0};
                    if (data.amount_untaxed === undefined) {data.amount_untaxed='0.00'};

                    setCartPriceQuantity('' + data['amount_untaxed'], '' + data['cart_quantity'], data['amount_untaxed']);
                    if (!data.quantity) { // update table and all prices on page
                        $(".oe_website_sale").find("div.row").load(location.href + " .oe_cart");
                        return;
                    }
                    $q.parent().parent().removeClass("hidden", !data.quantity);
                    //~ $q.html("(" + cart_quantity + ")");
                    $input.val(data.quantity);
                    $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                    $("#cart_total").replaceWith(data['website_sale.total']);
                    $.ajax({
                        url: '/shop/allowed_order/?order=' + $("a#process_checkout").data("order"),
                        type: 'post',
                        data: {},
                        success: function(data) {
                            if (data == '1') {
                                $("a#process_checkout").attr("disabled", false);
                                $("tr#value_not_met").addClass("hidden");
                            }
                            if (data == '0') {
                                $("a#process_checkout").attr("disabled", true);
                                $("tr#value_not_met").removeClass("hidden");
                            }
                        }
                    });
                });
            });
        });

        // hack to add and remove from cart with json
        $(oe_website_sale).on('click', 'a.js_add_cart_json', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.parent().parent().find("input");
            var min = parseFloat($input.data("min") || 0);
            var max = parseFloat($input.data("max") || Infinity);
            var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
            $input.val(quantity > min ? (quantity < max ? quantity : max) : min);
            //~ $('input[name="'+$input.attr("name")+'"]').val(quantity > min ? (quantity < max ? quantity : max) : min);
            $input.change();
            $("#top_menu").find("a[href*='/shop/cart']").closest("li").css({"display": "none"});
            return false;
        });

        $(oe_website_sale).on('click', 'a.js_remove_cart_json', function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.parent().parent().find("input");
            $input.val(0);
            $('input[name="'+$input.attr("name")+'"]').val(0);
            $input.change();
            if ($input.data('update_change')) {
                return;
            }
            var value = parseInt($input.val(), 10);
            var $dom = $input.closest('tr');
            var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
            var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            var line_id = parseInt($input.data('line-id'),10);
            var product_id = parseInt($input.data('product-id'),10);
            var product_ids = [product_id];
            $dom_optional.each(function(){
                product_ids.push($input.find('span[data-product-id]').data('product-id'));
            });
            if (isNaN(value)) value = 0;
            $input.data('update_change', true);
            openerp.jsonRpc("/shop/get_unit_price", 'call', {
                'product_ids': product_ids,
                'add_qty': value,
                'use_order_pricelist': true,
                'line_id': line_id})
            .then(function (res) {
                $dom.find('span.oe_currency_value').last().text(price_to_str(res[product_id]));
                $dom.find('.text-danger').toggle(res[product_id]<default_price && (default_price-res[product_id] > default_price/100));
                $dom_optional.each(function(){
                    var id = $input.find('span[data-product-id]').data('product-id');
                    var price = parseFloat($input.find(".text-danger > span.oe_currency_value").text());
                    $input.find("span.oe_currency_value").last().text(price_to_str(res[id]));
                    $input.find('.text-danger').toggle(res[id]<price && (price-res[id]>price/100));
                });
                openerp.jsonRpc("/shop/cart/update_json", 'call', {
                'line_id': line_id,
                'product_id': parseInt($input.data('product-id'),10),
                'set_qty': value})
                .then(function (data) {
                    $input.data('update_change', false);
                    var $q = $(".my_cart_quantity");
                    if (value !== parseInt($input.val(), 10)) {
                        $input.trigger('change');
                        return;
                    }
                    var cart_quantity = data.cart_quantity === undefined ? 0 : data.cart_quantity;
                    if (!data.quantity) {
                        $(".oe_website_sale").find("div.row").load(location.href + " .oe_cart");
                        $(".my_cart_total").load(location.href + " .my_cart_total");
                        $q.html("(" + cart_quantity + ")");
                        return;
                    }
                    $q.parent().parent().removeClass("hidden", !data.quantity);
                    $q.html("(" + cart_quantity + ")");
                    $input.val(data.quantity);
                    $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);
                    $("#cart_total").replaceWith(data['website_sale.total']);
                    $(".my_cart_total").load(location.href + " .my_cart_total");
                });
            });
            $("#top_menu").find("a[href='/shop/cart']").closest("li").css({"display": "none"});
            return false;
        });

        $('.oe_website_sale .a-submit:not(.dn_list_add_to_cart, .dn_list_add_to_cart_edu, #add_to_cart.a-submit, #add_to_cart_edu.a-submit), #comment .a-submit').off('click').on('click', function () {
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
            //~ update_product_info(this, +$(this).val());
        });


        $('div.js_product', oe_website_sale).each(function () {
            $('input.js_product_change', this).first().trigger('change');
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

    //~ if ($("#add_to_cart").is(":visible")) { $("div.css_quantity.input-group.oe_website_spinner").removeClass("hidden"); }
    //~ else { $("div.css_quantity.input-group.oe_website_spinner").addClass("hidden"); }

    //blink ok button when filter form input changed
    $("#desktop_product_navigator_filter").find(".checkbox").each(function() {
        $(this).on("change", function() {
            $(this).closest("form").find(".dn_ok").addClass("dn_blink");
        });
    });

    $("#desktop_product_navigator_filter").find(".category_checkbox").each(function() {
        var $self = $(this);
        $self.on("change", function() {
            check_in_check_out_parent();
            $self.closest("form").find(".dn_ok").addClass("dn_blink");
        });
    });

    $("#mobile_product_navigator_filter").find(".category_checkbox").each(function() {
        var $self = $(this);
        $self.on("change", function() {
            check_in_check_out_parent();
            $self.closest("form").find(".dn_ok").addClass("dn_blink");
        });
    });

    function check_in_check_out_parent() {
        var parent_categories = $("i.desktop_angle.fa").closest("h4").find("input.category_checkbox");
        $.each(parent_categories, function() {
            var $self = $(this);
            var checkin = true;
            var expand = false;
            $inputs = $("div#" + $self.data("category")).find("input.category_checkbox");
            $.each($inputs, function() {
                if (!$(this).is(":checked")) {
                    checkin = false;
                }
                else {
                    expand = true;
                }
            });
            if (!checkin) {
                $self.removeAttr("checked", "checked");
            }
            else {
                $self.attr("checked", "checked");
            }
            if (expand) {
                $self.removeClass("fa-angle-down");
                $self.addClass("fa-angle-up");
                $self.closest("a").removeClass("collapsed");
                $("div#" + $self.data("category")).addClass("in");
            }
        });
    }

    $("#dn_filter_modal").find(".checkbox").each(function() {
        $(this).on("change", function() {
            $(this).closest("form").find(".dn_ok").addClass("dn_blink");
        });
    });

    $("#dn_sort_modal").find(".radio").each(function() {
        $(this).on("change", function() {
            $(this).closest("form").find(".dn_ok").addClass("dn_blink");
        });
    });

    $(window).scroll(function() {
        if (dn_loading_products === false && ($(document).height() - $(window).scrollTop() - $(window).height() < 1000)) {
            dn_loading_products = true;
            if ($("#wrap").hasClass("autoload_grid")) {
                load_products_grid(current_page);
            }
            if ($("#wrap").hasClass("autoload_list")) {
                load_products_list(current_page);
            }
        }
    });

    //~ $(window).resize(function() {
        //~ var pm = $('div#payment_method');
        //~ if (pm !== undefined) {
            //~ var total = $('table#cart_total');
            //~ if (total !== undefined) {
                //~ pm.width(total.width());
            //~ }
        //~ }
    //~ });

});

function load_products_grid(page){
    var start_render = new Date();
    $('html,body').css('cursor', 'wait');
    $("div#loading").removeClass("hidden");
    var url = "/" + $("button#site_lang").data("lang") + "/dn_shop_json_grid";
    openerp.jsonRpc(url, "call", {
        'page': current_page.toString(),
    }).done(function(data){
        var product_count = 0;
        if (data['products'].length > 0) {
            var grid = $("#desktop_product_grid");
            $.each(data['products'], function(i) {
                grid.append(data['products'][i]);
                product_count ++;
            });
            current_page ++;
            dn_loading_products = false;
        }
        $('html,body').css('cursor', 'default');
        $("div#loading").addClass("hidden");
        var end_render  = new Date();
        var time_render = end_render.getTime() - start_render.getTime();
        console.log('Total', product_count, 'products load to html takes:', time_render, 'ms');
    });
}

function load_products_list(page){
    var start_render = new Date();
    $("div#loading").removeClass("hidden");
    $('html,body').css('cursor', 'wait');
    var url = "/" + $("button#site_lang").data("lang") + "/dn_shop_json_list";
    openerp.jsonRpc(url, "call", {
        'page': current_page,
    }).done(function(data){
        var product_count = 0;
        product_length = data['products'].length;
        if (data['products'].length > 0) {
            var tbody = $(".oe_website_sale").find('tbody');
            $.each(data['products'], function(i) {
                tbody.append(data['products'][i]);
                product_count ++;
            });
            current_page ++;
            dn_loading_products = false;
        }
        $('html,body').css('cursor', 'default');
        $("div#loading").addClass("hidden");
        var end_render  = new Date();
        var time_render = end_render.getTime() - start_render.getTime();
        console.log('Total', product_count, 'products load to html takes:', time_render, 'ms');
    });
}

var timer = function(name) {
    var start = new Date();
    return {
        stop: function() {
            var end  = new Date();
            var time = end.getTime() - start.getTime();
            console.log('Timer:', name, 'finished in', time, 'ms');
        }
    }
};

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
    $("#webshop_dermanord_mobile_filter_modal").find(".panel-group").find("input[type=checkbox]").each(
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

$(document).on('click', '.dn_js_options ul[name="style"] a', function (event) {
    var $a = $(event.currentTarget);
    var $li = $a.parent();
    var $data = $a.parents(".dn_js_options:first");
    var $product = $a.closest(".dn_oe_product").find(".dn_product_div");

    $li.parent().removeClass("active");
    openerp.jsonRpc('/shop/change_styles', 'call', {'id': $data.data('id'), 'style_id': $a.data("id")})
        .then(function (result) {
            $product.toggleClass($a.data("class"));
            $li.toggleClass("active", result);
        });
});

// This method called by "add_to_cart" button in both dn_shop and dn_list.
// Method does a calculation according to the product unit_price * quantity and update the cart total amount.
// Method does a RPC-call, after response update cart again with current order total amount.
$(document).on('click', '.dn_list_add_to_cart, .dn_list_add_to_cart_edu, #add_to_cart.a-submit, #add_to_cart_edu.a-submit', function (event) {
    var self = $(this);
    var my_cart_total = $(".my_cart_total");
    my_cart_total.closest("a").css({"pointer-events": "none", "cursor": "default"});
    my_cart_total.closest("a").attr("id", "");
    self.attr("data-finished", "");
    var formData = JSON.stringify($(this).closest("form").serializeArray());
    var form_arr = JSON.parse(formData);
    var product_id = "0";
    var add_qty = "0";
    $.each(form_arr, function(key, info){
        if(info['name'] == "product_id") {
            product_id = info['value'];
        }
        if(info['name'] == "add_qty") {
            add_qty = info['value'];
        }
    });

    if ($(this).closest("tr").length == 0) {
        // unit price in dn_shop product detail view
        if (lang == 'en-US'){
            var unit_price = parseFloat($(this).closest("form").find(".oe_price").text());
        }
        else{
            var unit_price = parseFloat($(this).closest("form").find(".oe_price").text().replace(",", "."));
        }
    }
    else {
        // unit price in dn_list
        var unit_price = parseFloat($(this).closest("tr").closest("tr").find(".your_price").data("price"));
    }
    //~ var unit_tax = parseFloat($(this).closest("tr").find(".your_price").data("tax"));
    var cart_sum = $(".my_cart_total").html();
    //~ if (lang == 'en-US'){
        //~ var cart_total = parseFloat(cart_sum.replace(",", ""));
    //~ }
    //~ else{
        //~ var cart_total = parseFloat(cart_sum.replace(" ", "").replace(",", "."));
    //~ }
    var cart_total = $(".my_cart_quantity").data("price");
    var cart_html = $(".my_cart_quantity").html();
    var cart_qty = cart_html.substring(cart_html.lastIndexOf("(")+1,cart_html.lastIndexOf(")"));
    var current_total = cart_total + unit_price * parseFloat(add_qty);
    setCartPriceQuantity(parseFloat(current_total).toFixed(2), '' + (parseInt(add_qty) + parseInt(cart_qty)), current_total);

    openerp.jsonRpc("/shop/cart/update", "call", {
        'product_id': product_id,
        'add_qty': add_qty
    }).done(function(data){
        if($.isArray(data)){
            self.attr("data-finished", "done");
            if ($(".dn_list_add_to_cart[data-finished='']").length == 0 || $(".dn_list_add_to_cart_edu[data-finished='']").length == 0) {
                setCartPriceQuantity(data[0], data[1], data[2]);
                my_cart_total.closest("a").css({"pointer-events": "", "cursor": ""});
                my_cart_total.closest("a").attr("id", "cart_updated");
            }
        }
        else {
            window.alert(data);
        }
    });
});
