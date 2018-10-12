var website = openerp.website;
website.add_template_file('/news_dermanord/static/src/xml/templates.xml');

var current_page = 0;

$(document).ready(function() {
    $('.js_fullheight').css('min-height', '540px');
    resize_blog_background_image();
    $(window).scroll(function() {
        if ($(window).scrollTop() + $(window).height() == $(document).height()) {
            if ($('.blog_list_item').length > 0) {
                load_blog_post_list(current_page);
            }
        }
    });
});

function load_blog_post_list(page){
    openerp.jsonRpc("/website_blog_json_list", "call", {
        'page': page,
    }).done(function(data){
        var page_count = data['page'];
        if (page_count >= current_page) {
            var blog_content = '';
            $.each(data['blog_posts'], function(key, info) {
                var content = openerp.qweb.render('blog_post_item', {
                    'background_image_css': data['blog_posts'][key]['background_image_css'],
                    'post_name': data['blog_posts'][key]['post_name'],
                    'post_subtitle': data['blog_posts'][key]['post_subtitle'],
                    'date_start': data['blog_posts'][key]['date_start'],
                    'tags_html': data['blog_posts'][key]['tags_html'],
                    'post_url': data['blog_posts'][key]['post_url'],
                    'str_read_more': data['blog_posts'][key]['str_read_more'],
                    'str_tags': data['blog_posts'][key]['str_tags']
                });
                blog_content += content;
            });
            $(".blog_list_item.mb32").find(".row").append(blog_content);
            current_page ++;
        }
    });
}

$(window).resize(function() {
    resize_blog_background_image();
});

function resize_blog_background_image() {
    var width = $("div.blog_background_image_list").width();
    if($(window).width() < 768) { // xs
        //~ var img_height = 253;
        var img_height = width * 450 / 1366 + 32;
    }
    if($(window).width() >= 768 && $(window).width() < 986) { // sm
        //~ var img_height = 326;
        var img_height = width * 450 / 1366 + 32;
        $("div.blog_content_div").css({"max-height": img_height + 50});
    }
    if($(window).width() >= 986 && $(window).width() < 1200) { //md
        //~ var img_height = 164;
        var img_height = width * 450 / 1366 + 32;
        $("div.blog_content_div").css({"max-height": img_height + 100});
    }
    if($(window).width() >= 1200) { //lg
        //~ var img_height = 188;
        var img_height = width * 450 / 1366 + 32;
        $("div.blog_content_div").css({"max-height": img_height + 32});
    }
    $("div.blog_background_image_list").css({"max-height": img_height});
}
