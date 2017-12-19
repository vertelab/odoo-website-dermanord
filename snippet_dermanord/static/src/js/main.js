var categ_block_hidden_indicator = 1;

$(document).ready(function() {

    openerp.jsonRpc("/category_snippet/get_p_categories", "call", {
    }).done(function(data){
        if (data.length == 0) {
            var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No category yet</h2>';
            //~ self.$target.find("h3").after(message);
        }
        else {
            var category_content = '';
            var show_more_block = "<h3 id='show_more_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm' style='color: #fff; text-decoration: underline;'>Show More <i class='fa fa-angle-down'/></h3>";
            var show_less_block = "<h3 id='show_less_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm hidden' style='color: #fff; text-decoration: underline;'>Show Less <i class='fa fa-angle-up'/></h3>";
            i = 0;
            $.each(data, function(key, info) {
                var content = '<a href="/dn_shop/category/' + data[key]['id'] + '"><div class="categ_block col-md-4 col-xs-12"><img class="img img-responsive categ_block_img" src="' + data[key]['image'] + '"/><div class="container"><h2 class="categ_block_text dn_uppercase">' + '<span>' + data[key]['name'] + '</span></h2></div></div></a>';
                category_content += i > categ_block_hidden_indicator ? content.replace("categ_block", "categ_block extra_block hidden-xs") : content;
                if(i == categ_block_hidden_indicator){
                    category_content += show_more_block;
                }
                i ++;
            });
            category_content += show_less_block;
            $(".category_div").html(category_content).text();
            $("#show_more_block").click(function() {
                $("#show_less_block").removeClass("hidden");
                $("#show_more_block").addClass("hidden");
                $.each($(".categ_p_section").find(".extra_block"), function(){
                    $(this).removeClass("hidden-xs");
                });
            });
            $("#show_less_block").click(function() {
                $("#show_more_block").removeClass("hidden");
                $("#show_less_block").addClass("hidden");
                $.each($(".categ_p_section").find(".extra_block"), function(){
                    $(this).addClass("hidden-xs");
                });
            });
        }
    });

    openerp.jsonRpc("/get_sale_promotions", "call", {
    }).done(function(data){
        if (data.length == 0) {
            var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No sale and promotions yet</h2>';
            //~ self.$target.find("h3").after(message);
        }
        else {
            var indicator_content = '';
            var sp_content = '';
            i = 0;
            $.each(data, function(key, info) {
                var is_active = i == 0 ? "item active" : "item";
                var i_content = '<li class="' + (i == 0 ? "active": "") + '" data-slide-to="' + i + '" data-target="#sale_promotions"/>';
                var content = '<div class="' + is_active + '"><a href="' + data[key]['url'] + '"><img class="img-responsive sale_promotions_img" src="' + data[key]['image'] + '"/><div class="container"><div class="row content"><div class="col-md-12 col-sm-12"><h4 class="mb16 dn_uppercase">' + data[key]['name'] + '</h4><h5 class="mb16">' + data[key]['description'] + '</h5></div></div></div></a></div>';
                indicator_content += i_content;
                sp_content += content;
                i ++;
            });
            $(".sale_promotions_indicators").html(indicator_content);
            $(".sale_promotions_content").html(sp_content);
            $(".sale_promotions").find(".carousel.slide").each(function() {
                var carousel_id = $(this).attr("id");
                $($(this).find("li")).each(function() {
                    $(this).attr("data-target", "#" + carousel_id);
                });
            });
        }
    });

    openerp.jsonRpc("/product_hightlights_snippet/get_highlighted_products", "call", {
        'campaign_date': '',
    }).done(function(data){
        if (data.length == 0) {
            //~ var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No product highlight yet</h2>';
            var message = '<h2 class="text-center text-muted">No product highlight yet</h2>';
            $(".product_div").html(message);
        }
        else {
            var ph_content = '';
            $.each(data, function(key, info) {
                var content = '<a href="' + data[key]['url'] + '"><div class="col-md-3 col-sm-6 col-xs-12"><div class="ph_block"><img class="img img-responsive ph_img" src="' + data[key]['image'] + '"/><div class="container desc_div"><h4 class="dn_uppercase">' + data[key]['name'] + '</h4><p class="ph_desc text-muted">' + data[key]['description'] + '</p></div></div></div></a>';
                ph_content += content;
            });
            $(".product_div").html(ph_content).text();
        }
    });

    //~ $(".di_mobile_img_edit").each(function(){
        //~ console.log($(this).attr("src"));
        //~ var mobile_img = $(this).closest(".item").find(".di_mobile_img");
        //~ console.log(mobile_img);
        //~ mobile_img.attr("src", $(this).attr("src"));
        //~ $(this).addClass("css_non_editable_mode_hidden");
    //~ });

    //~ $(".carousel-inner").swiperight(function() {
          //~ $(this).parent().carousel('prev');
            //~ });
       //~ $(".carousel-inner").swipeleft(function() {
          //~ $(this).parent().carousel('next');
   //~ });

});