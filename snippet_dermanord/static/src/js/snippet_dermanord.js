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
                        'background_image': data[key]['background_image'],
                    });
                    //~ content = content.replace("/blog/blog_id/post/post_id", ("/blog/" + data[key]['blog_id'] + "/post/" + key));
                    blog_content += content;
                    i ++;
                });
                self.$target.find(".blog_banner_content").html(blog_content);
            });
        }
    }
});

//~ website.snippet.options.sale_promotions_option = website.snippet.Option.extend({
    //~ drop_and_build_snippet: function () {
        //~ this.get_sp();
    //~ },
    //~ get_sp: function(){
        //~ var self = this;
        //~ openerp.jsonRpc("/get_sale_promotions", "call", {
        //~ }).done(function(data){
            //~ if (data.length == 0) {
                //~ var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No sale and promotions yet</h2>';
                //~ self.$target.find("h3").after(message);
            //~ }
            //~ else {
                //~ var indicator_content = '';
                //~ var sp_content = '';
                //~ i = 0;
                //~ $.each(data, function(key, info) {
                    //~ var i_content = openerp.qweb.render('sale_promotions_indicators', {
                        //~ 'indicator': i == 0 ? "active" : "",
                        //~ 'slide_nr': i,
                    //~ });
                    //~ var content = openerp.qweb.render('sale_promotions_content', {
                        //~ 'sp_url': data[key]['url'],
                        //~ 'item_content': i == 0 ? "item active" : "item",
                        //~ 'sp_name': data[key]['name'],
                        //~ 'sp_description': data[key]['description'],
                        //~ 'background_image': data[key]['image'],
                    //~ });
                    //~ indicator_content += i_content;
                    //~ sp_content += content;
                    //~ i ++;
                //~ });
                //~ self.$target.find(".sale_promotions_indicators").html(indicator_content);
                //~ self.$target.find(".sale_promotions_content").html(sp_content);
            //~ }
        //~ });
    //~ }
//~ });

website.snippet.options.categ_p_option = website.snippet.Option.extend({
    drop_and_build_snippet: function () {
        this.get_categories();
    },
    get_categories: function(){
        var self = this;
        openerp.jsonRpc("/category_snippet/get_p_categories", "call", {
        }).done(function(data){
            if (data.length == 0) {
                var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No category yet</h2>';
                self.$target.find("h3").after(message);
            }
            else {
                var category_content = '';
                var show_more_block = "<h3 id='show_more_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm' style='color: #fff; text-decoration: underline;'>Show More <i class='fa fa-angle-down'/></h3>";
                var show_less_block = "<h3 id='show_less_block' class='text-center mt16 mb16 hidden-lg hidden-md hidden-sm hidden' style='color: #fff; text-decoration: underline;'>Show Less <i class='fa fa-angle-up'/></h3>";
                i = 0;
                $.each(data, function(key, info) {
                    var content = openerp.qweb.render('p_category_snippet', {
                        'category_name': data[key]['name'],
                        'category_image': data[key]['image'],
                    });
                    content = content.replace("/dn_shop/category/category_id", "/dn_shop/category/" + data[key]['id']);
                    category_content += i > categ_block_hidden_indicator ? content.replace("categ_block", "categ_block extra_block hidden-xs") : content;
                    if(i == categ_block_hidden_indicator){
                        category_content += show_more_block;
                    }
                    i ++;
                });
                category_content += show_less_block;
                self.$target.find(".category_div").html(category_content);
            }
        });
    }
});

website.snippet.options.product_highlights_option = website.snippet.Option.extend({
    //~ start: function () {
        //~ var self = this;
        //~ this._super();
        //~ this.$el.find(".oe_product_highlights").on('click', function () {
            //~ self.get_highlighted_products();
        //~ });
        //~ this.$el.find(".oe_ph_col_change").on('click', function () {
            //~ self.col_change($(this).attr("data-value"));
        //~ });
    //~ },
    drop_and_build_snippet: function () {
        this.get_highlighted_products();
    },
    get_highlighted_products: function(){
        var self = this;
        openerp.jsonRpc("/product_hightlights_snippet/get_highlighted_products", "call", {
            'campaign_date': '',
        }).done(function(data){
            if (data.length == 0) {
                var message = '<h2 class="text-center text-muted css_non_editable_mode_hidden">No product highlight yet</h2>';
                self.$target.find("h3").after(message);
            }
            else {
            var ph_content = '';
                $.each(data, function(key, info) {
                    var content = openerp.qweb.render('product_highlights_snippet', {
                        'ph_url': data[key]['url'],
                        'ph_name': data[key]['name'],
                        'ph_image': data[key]['image'],
                        'ph_description': data[key]['description'],
                    });
                    //~ content = content.replace("product_highlight_link", data[key]['url']);
                    ph_content += content;
                });
                self.$target.find(".product_div").html(ph_content);
            }
        });
    }
    //~ col_change: function(col) {
        //~ var self = this;
        //~ self.$target.find(".ph_block").attr({
            //~ "class": "ph_block col-md-" + col
        //~ });
    //~ }
});
