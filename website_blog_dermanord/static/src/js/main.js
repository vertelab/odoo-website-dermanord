$(document).ready(function() {
    resize_blog_bg_image();
});

$(window).resize(function() {
    resize_blog_bg_image();
});

function resize_blog_bg_image() {
    if($(window).width() < 992) {
        $(".blog_background_image_list").css({"height": $(".blog_background_image_list").width() / 3.035555556});
    }
}
