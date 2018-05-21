var search_icron = $("#top_menu").find("#search-btn-modal").closest("li");
var shop_cart = $("#top_menu").find("a[href$='/shop/cart']").closest("li");
var divider = $("#top_menu").find(".divider").closest("li");
var my_account = $("#top_menu > li").last();
var more_menu = $("#top_menu").find("li#more_dropdown");
//~ var total_height_before_main = 0;
var menu_items = [];

openerp.website.add_template_file('/theme_dermanord/static/src/xml/theme_dermanord.xml');

$("#top_menu").children().each(function() { // those menu items should not included in more menu
    if($(this).attr("id") == "fts_search_btn")
        return false;
    else if($(this).attr("class") == "hidden-xs")
        return false;
    else if($(this).attr("class") == "divider")
        return false;
    else if($(this).attr("id") != "more_dropdown")
        menu_items.push($(this));
});

var li_width_init = my_account.width(); // initial with of menu bar
if(menu_items.length != 0) {
    li_width_init += more_menu.width();
}

jQuery.expr[':'].contains = function(a, i, m) {
    return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
};

dermanord_resize_for_menu = function() {
    //~ $("main").prevAll().each(function(){
        //~ total_height_before_main += $(this).height();
    //~ });
    if($(window).width() > 758) {
        var max_li_width = $("#top_menu").width() - li_width_init;
        var li_width = 0;
        $.each(menu_items, function(index) {
            more_menu_item = more_menu.find('a[href="' + $(this).find('a').attr('href') + '"]');
            if (more_menu_item.length == 1){
                li_width += $(this).width();
                if (li_width > max_li_width) { // hide this menu item from menu bar and show it in more menu
                    $(this).closest("li").css({"display": "none"});
                    more_menu_item.css({"display": "block"});
                }
                else {  // show this menu item in menu bar again and hide it from more menu
                    $(this).closest("li").css({"display": "block"});
                    more_menu_item.css({"display": "none"});
                }
            }
        });

        // determine if more menu should show up or not
        if (more_menu.prev().is(':visible')) { more_menu.addClass("hidden"); }
        else { more_menu.removeClass("hidden") };

        //~ menu = $(".collapse.navbar-collapse.navbar-top-collapse");
        menu = $(".navbar.navbar-default.navbar-static-top");
        bt = menu.css('border-top-width');
        bb = menu.css('border-bottom-width');
        height = menu.height() + parseFloat(bt.substring(0, bt.length-2)) + parseFloat(bb.substring(0, bb.length-2));
        breadcrumb = $("ol.dn_breadcrumb");
        if(breadcrumb.length == 1) {
            breadcrumb.css({"margin-top": height});
        }
        else {
            $(".container.dn_header").css({"margin-top": height});
        }
        $(".oe_website_login_container").css({"margin-top": height});
    }
    else {
        $(".container.dn_header").css({"margin-top": ""});
        $(".oe_website_login_container").css({"margin-top": ""});
        $("ol.dn_breadcrumb").css({"margin-top": ""});
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
    // hide shopping cart
    shop_cart.addClass("hidden");
    // hide divider
    divider.addClass("hidden");
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
    setActive();

    $('#search_modal').on('shown.bs.modal', function() {
        $(this).find('[name=search]').focus();
    });

    $("#search_modal").on('hidden.bs.modal', function(){
        $(this).find("#searchbox").find("li").each(function(){
            if ($(this).attr("selected") == "selected") {
                $(this).removeAttr("selected");
            }
        });
    });
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

// this method set the parent menu as active when current menu is active.
function setActive() {
    var path = window.location.pathname;
    openerp.jsonRpc("/get_parent_menu", "call", {
        'url': path,
    }).done(function(data){
        $("#top_menu a").each(function(){
            if ($(this).attr("href") == data) {
                $(this).closest("li").addClass("active");
            }
        });
    });
}

var chosen = "";
$(document).keydown(function(e){ // 38-up, 40-down
    if ($("#searchbox").has("li")) {
        if (e.keyCode == 40) {
            $(".add-on").find('[name=search]').blur();
            var li_size = $("#searchbox").find("li").size();
            if (li_size != 0) {
                var li_size_selected = $("#searchbox").find("li[selected=selected]").size();
                if (li_size_selected == 0) {
                    $("#searchbox").find("li").first().attr("selected", "selected");
                }
                else {
                    var found = false;
                    var select_next = false;
                    $("#searchbox").find("li").each(function(){
                        if (select_next) {
                            $(this).attr("selected", "selected");
                            found = true;
                            select_next = false;
                        }
                        else if ($(this).attr("selected") == "selected") {
                            $(this).removeAttr("selected");
                            select_next = true;
                        }
                    });
                    if (!found) {
                        $("#searchbox").find("li").first().attr("selected", "selected");
                    }
                }
            }
            return false;
        }
        if (e.keyCode == 38) {
            $(".add-on").find('[name=search]').blur();
            var li_size = $("#searchbox").find("li").size();
            if (li_size != 0) {
                var li_size_selected = $("#searchbox").find("li[selected=selected]").size();
                if (li_size_selected == 0) {
                    $("#searchbox").find("li").first().attr("selected", "selected");
                }
                else {
                    var found = false;
                    var select_next = false;
                    $($("#searchbox").find("li").get().reverse()).each(function(){
                        if (select_next) {
                            $(this).attr("selected", "selected");
                            found = true;
                            select_next = false;
                        }
                        else if ($(this).attr("selected") == "selected") {
                            $(this).removeAttr("selected");
                            select_next = true;
                        }
                    });
                    if (!found) {
                        $("#searchbox").find("li").last().attr("selected", "selected");
                    }
                }
            }
            return false;
        }
        if (e.keyCode == 13) {
            $("#searchbox").find("li").each(function() {
                if ($(this).attr("selected") == "selected") {
                    window.location.replace($(this).find("a").attr("href"));;
                }
            });
        }
    }
});
