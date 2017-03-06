var website = openerp.website;
website.add_template_file('/snippet_dermanord/static/src/xml/snippets.xml');
var categ_block_hidden_indicator = 1;

website.snippet.options.blog_banner_option = website.snippet.Option.extend({
    start: function () {
        var self = this;
        this._super();
        this.$el.find(".oe_blog_banner_change").on('click', function () {
            self.get_blogs($(this).attr("data-value"));
        });
    },
    get_blogs: function(blog_id){
        if (blog_id != '') {
            var self = this;
            openerp.jsonRpc("/blog_banner_snippet/blog_banner_change", "call", {
                'blog_id': blog_id,
            }).done(function(data){
                var blog_content = '';
                i = 0;
                $.each(data, function(key, info) {
                    var content = openerp.qweb.render('blog_banner_content', {
                        'item_content': i == 0 ? "item active" : "item",
                        'blog_name': data[key]['name'],
                        'background_image': data[key]['background_image'] != null ? data[key]['background_image'] : '',
                    });
                    content = content.replace("/blog/blog_id/post/post_id", ("/blog/" + data[key]['blog_id'] + "/post/" + key));
                    blog_content += content;
                    i ++;
                });
                self.$target.find(".blog_banner_content").html(blog_content);
            });
        }
    }
});

website.snippet.options.blog_slide_option = website.snippet.Option.extend({
    start: function () {
        var self = this;
        this._super();
        this.$el.find(".oe_blog_slide").on('click', function () {
            self.get_blogs($(this).attr("data-value"));
        });
    },
    get_blogs: function(){
        var self = this;
        openerp.jsonRpc("/blog_slide_snippet/blog_slide_change", "call", {
        }).done(function(data){
            self.$target.find(".oe_bs_title").html(data['blog_name']);
            //~ var indicator_content = '';
            var blog_content = '';
            i = 0;
            $.each(data['posts'], function(key, info) {
                //~ var i_content = openerp.qweb.render('blog_slide_indicators', {
                    //~ 'indicator': i == 0 ? "active" : "",
                    //~ 'slid_nr': i,
                //~ });
                var content = openerp.qweb.render('blog_slide_content', {
                    'item_content': i == 0 ? "item active" : "item",
                    'blog_name': data['posts'][key]['name'],
                    'blog_subtitle': data['posts'][key]['subtitle'],
                    'background_image': data['posts'][key]['background_image'] != null ? data['posts'][key]['background_image'] : '',
                });
                //~ indicator_content += i_content;
                content = content.replace("/blog/blog_id/post/post_id", ("/blog/" + data['posts'][key]['blog_id'] + "/post/" + key));
                blog_content += content;
                i ++;
            });
            //~ self.$target.find(".blog_slide_indicators").html(indicator_content);
            self.$target.find(".blog_slide_content").html(blog_content);
        });
    }
});

website.snippet.options.categ_p_option = website.snippet.Option.extend({
    start: function () {
        var self = this;
        this._super();
        this.$el.find(".oe_p_categories").on('click', function () {
            self.get_categories();
        });
        this.$el.find(".oe_c_col_change").on('click', function () {
            self.col_change($(this).attr("data-value"));
        });
    },
    get_categories: function(){
        var self = this;
        openerp.jsonRpc("/category_snippet/get_p_categories", "call", {
        }).done(function(data){
            var category_content = '';
            var show_more_block = "<h3 id='show_more_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm' style='color: #fff; text-decoration: underline;'>Show More <i class='fa fa-angle-down'/></h3>";
            var show_less_block = "<h3 id='show_less_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm hidden' style='color: #fff; text-decoration: underline;'>Show Less <i class='fa fa-angle-up'/></h3>";
            i = 0;
            $.each(data, function(key, info) {
                var content = openerp.qweb.render('p_category_snippet', {
                    'category_name': data[key]['name'],
                    'category_image': data[key]['image'] != null ? ("data:image/png;base64," + data[key]['image']) : '',
                });
                content = content.replace("/shop/category/category_id", "/shop/category/" + key);
                category_content += i > categ_block_hidden_indicator ? content.replace("categ_block", "categ_block extra_block hidden-xs") : content;
                if(i == categ_block_hidden_indicator){
                    category_content += show_more_block;
                }
                i ++;
            });
            category_content += show_less_block;
            self.$target.find(".category_div").html(category_content);
        });
    },
    col_change: function(col) {
        var self = this;
        self.$target.find(".categ_block:not(.extra_block)").attr({
            "class": "categ_block col-md-" + col
        });
        self.$target.find(".extra_block").attr({
            "class": "categ_block extra_block hidden-xs col-md-" + col
        });
    }
});

website.snippet.options.product_highlights_option = website.snippet.Option.extend({
    start: function () {
        var self = this;
        this._super();
        this.$el.find(".oe_product_highlights").on('click', function () {
            self.get_highlighted_products();
        });
        this.$el.find(".oe_ph_col_change").on('click', function () {
            self.col_change($(this).attr("data-value"));
        });
    },
    get_highlighted_products: function(){
        var self = this;
        openerp.jsonRpc("/product_hightlights_snippet/get_highlighted_products", "call", {
        }).done(function(data){
            var ph_content = '';
            $.each(data, function(key, info) {
                var content = openerp.qweb.render('product_highlights_snippet', {
                    'ph_name': data[key]['name'],
                    'ph_image': data[key]['image'],
                    'ph_description': data[key]['description_sale'],
                });
                content = content.replace("shop/product/product_id", "/shop/product/" + key);
                ph_content += content;
            });
            self.$target.find(".product_div").html(ph_content);
        });
    },
    col_change: function(col) {
        var self = this;
        self.$target.find(".ph_block").attr({
            "class": "ph_block col-md-" + col
        });
    }
});

$(document).ready(function() {
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
    //~ $(".carousel-inner").swiperight(function() {
          //~ $(this).parent().carousel('prev');
            //~ });
       //~ $(".carousel-inner").swipeleft(function() {
          //~ $(this).parent().carousel('next');
   //~ });
});
