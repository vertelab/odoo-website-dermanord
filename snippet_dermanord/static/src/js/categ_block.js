var website = openerp.website;
website.add_template_file('/snippet_dermanord/static/src/xml/category_snippet.xml');

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
            $.each(data, function(key, info) {
                var content = openerp.qweb.render('p_category_snippet', {
                    'category_name': data[key]['name'],
                    'category_image': data[key]['image'] != null ? ("data:image/png;base64," + data[key]['image']) : '',
                });
                console.log(data[key]['image']);
                category_content += content;
            });
            self.$target.find(".category_div").html(category_content);
        });
    },
    col_change: function(col) {
        var self = this;
        self.$target.find(".categ_block").attr({
            "class": "categ_block col-md-" + col
        });
    }
});

$(document).ready(function() {
});
