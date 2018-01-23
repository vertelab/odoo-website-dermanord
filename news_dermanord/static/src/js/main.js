var website = openerp.website;
website.add_template_file('/news_dermanord/static/src/xml/templates.xml');

var current_page = 0;

$(document).ready(function() {
    $('.js_fullheight').css('min-height', '540px');

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
                    'write_date': data['blog_posts'][key]['write_date'],
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
