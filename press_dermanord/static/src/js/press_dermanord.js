$(".img_press_block").each(function () {
    var img_url = $(this).find(".img_2_change").attr("src");
    if(img_url.indexOf("imagemagick") == -1) {
        var id = img_url.substring(img_url.lastIndexOf("ir.attachment/")+14, img_url.lastIndexOf("_"));
        $(this).find(".img_press_website").attr("href", "/imagefield/ir.attachment/datas/" + id + "/ref/press_dermanord.image_website");
        $(this).find(".img_press_original").attr("href", "/imagefield/ir.attachment/datas/" + id + "/ref/press_dermanord.image_original");
        $(this).find(".img_2_change").attr("src", "/imagefield/ir.attachment/datas/" + id + "/ref/press_dermanord.image_thumbnail");
        //~ $(this).find(".img_press_website").attr("href", "/imagemagick/" + id + "/id/" + $(".website_recipe").attr("id"));
        //~ $(this).find(".img_press_original").attr("href", "/imagemagick/" + id + "/id/" + $(".original_recipe").attr("id"));
        //~ $(this).find(".img_2_change").attr("src", "/imagemagick/" + id + "/id/" + $(".thumbnail_recipe").attr("id"));
    }
});


