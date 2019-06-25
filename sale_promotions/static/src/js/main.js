$(document).ready(function(){
    // diactived slide function
    //~ var content_html = '';
    //~ $(".sp_div").find("div[class^='sp_']").each(function(e){
        //~ var content = $(this).html();
        //~ if (e == 0) {
            //~ content = content.replace("sale_promotions_img", "item active");
        //~ }
        //~ else {
            //~ content = content.replace("sale_promotions_img", "item");
        //~ }
        //~ content_html += content;
    //~ });
    //~ $("#sp_div_mobile").find(".carousel-inner").html(content_html);

    update_sale_promotions($(".sp_div").find(".sp_one_two"), $(".sp_div").find(".sp_one_two").find(".sale_promotions_img").attr("style"));

    $(".sp_div").find(".sp_one_one").each(function() {
        update_sale_promotions($(this), $(this).find(".sale_promotions_img").attr("style"));
    });

    update_sale_promotions($(".sp_div").find(".hidden-xs").find(".sp_two_one"), $(".sp_div").find(".hidden-xs").find(".sp_two_one").find(".sale_promotions_img").attr("style"));

    update_sale_promotions($(".sp_div").find(".hidden-lg.hidden-md.hidden-sm").find(".sp_two_one"), $(".sp_div").find(".hidden-xs").find(".sp_two_one").find(".sale_promotions_img").attr("style"));

    function update_sale_promotions(div, style){
        if (div!==undefined && style!==undefined) {
            var sp_id = style.split("/")[4];
            var tclass = div.attr("class");
            openerp.jsonRpc("/get_sale_promotion", "call", {
                'sp_id': sp_id,
                'target_class': tclass
            }).done(function(data){
                var img_src = "background-image: url('" + data['image'] + "');";
                div.html('<a href="' + data['url'] + '"><div class="img img-responsive sale_promotions_img" style="' + img_src +'"></div></a>');
            });
        }
    }

});
