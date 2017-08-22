var search_icron = $("#top_menu").find("#search-btn-modal").closest("li");
var shop_cart = $("#top_menu").find("a[href='/shop/cart']").closest("li");
var divider = $("#top_menu").find(".divider").closest("li");
var my_account = $("#top_menu").find(".dropdown-menu.js_usermenu").closest("li");
var more_menu = $("#top_menu").find("li#more_dropdown");
var menu_items = [];
var more_menu_items = [];
$("#top_menu").children().each(function() {
    if($(this).attr("id") == "fts_search_btn")
        return false;
    else if($(this).attr("class") == "hidden-xs")
        return false;
    else if($(this).attr("class") == "divider")
        return false;
    else if($(this).attr("id") != "more_dropdown")
        menu_items.push($(this));
});
$("#top_menu").find("#more_dropdown").find("ul").children().each(function() {
    more_menu_items.push($(this));
});

var li_width_init = search_icron.width() + shop_cart.width() + divider.width() + my_account.width() + 40; // extra pixels to avoid change row
if(menu_items.length == 0) {
    more_menu.addClass("hidden");
}
else if(menu_items.length != 0) {
    more_menu.removeClass("hidden");
    li_width_init += more_menu.width();
}

jQuery.expr[':'].contains = function(a, i, m) {
    return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
};

dermanord_resize_for_menu = function() {
    if($(window).width() > 758) {
        var max_li_width = $("#top_menu").width() - li_width_init;
        var li_width = 0;
        $.each(menu_items, function(index) {
            li_width += $(this).width();
            if (li_width > max_li_width) {
                $(this).css({"display": "none"});
            }
            else {
                more_menu_items[index].css({"display": "none"});
            }
        });
        //~ menu = $(".collapse.navbar-collapse.navbar-top-collapse");
        menu = $(".navbar.navbar-default.navbar-static-top");
        bt = menu.css('border-top-width');
        bb = menu.css('border-bottom-width');
        height = menu.height() + parseFloat(bt.substring(0, bt.length-2)) + parseFloat(bb.substring(0, bb.length-2));
        $(".container.dn_header").css({"margin-top": height});
        $(".oe_website_login_container").css({"margin-top": height});
        if ($("#wrap").prev()[0].className == "breadcrumb") {
            $("ol.breadcrumb").css({"margin-top": height});
        }
    }
    else {
        $(".container.dn_header").css({"margin-top": ""});
        $(".oe_website_login_container").css({"margin-top": ""});
        $("ol.breadcrumb").css({"margin-top": ""});
    }
}

dermanord_set_menu_margin = function() {
    nav = $('#oe_main_menu_navbar');
    if (nav.length == 1) {
        bt = nav.css('border-top-width');
        bb = nav.css('border-bottom-width');
        height = (nav.height() + parseFloat(bt.substring(0, bt.length-2)) + parseFloat(bb.substring(0, bb.length-2))) - $(document).scrollTop();
        if (height < 0) {
            height = 0;
        }
        mt = $(".navbar.navbar-default.navbar-static-top").css('margin-top');
        if (height != parseFloat(mt.substring(0, mt.length-2))) {
            $(".navbar.navbar-default.navbar-static-top").css({'margin-top': height});
        }
    }
}

$(document).ready(function() {
    if ($("#wrap").closest.className == "container dn_header") {
        static_margin = $(".container.dn_header").height();
    }
    $("#search-btn").click(function(){ $("#search_input").toggle(); });
    dermanord_resize_for_menu();
    dermanord_set_menu_margin();
    var brand = $('*:contains("MARIA ÅKERBERG")');
    brand.each(function(index) {
        if ($(brand[index]).is("h1, h2, h3, h4, h5, h6, p, a, strong, b, u, mark, small")) {
            var brand_text = brand[index].innerHTML.replace(/MARIA ÅKERBERG/g, "MARIA&#160;ÅKERBERG");
            $(brand[index]).html(brand_text);
        }
    });
    if ($(".dn_header_container").height() != 0) {
        $(".dn_header_nav").css({"height": $(".dn_header_container").height()});
    }
    else if ($(".dn_header_container").height() == 0) {
        $(".dn_header_nav").css({"height": $(".dn_header_nav").find(".nav-stacked").height() + 15});
    }
});

$(window).resize(function() {
    dermanord_resize_for_menu();
    if ($(".dn_header_container").height() != 0) {
        $(".dn_header_nav").css({"height": $(".dn_header_container").height()});
    }
    else if ($(".dn_header_container").height() == 0) {
        $(".dn_header_nav").css({"height": $(".dn_header_nav").find(".nav-stacked").height() + 15});
    }
});

$(window).scroll(function() {
    dermanord_set_menu_margin();
});

