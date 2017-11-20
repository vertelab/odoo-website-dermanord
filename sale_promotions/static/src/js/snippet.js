var website = openerp.website;
website.add_template_file('/sale_promotions/static/src/xml/templates.xml');

website.snippet.options.sale_promotions_option = website.snippet.Option.extend({
    start: function () {
        var self = this;
        this._super();
        this.$el.find(".oe_sp_change").on('click', function () {
            self.get_sp($(this).attr("data-id"));
        });
    },
    get_sp: function get_sale_promotions(sp_id){
        if (sp_id != "") {
            var self = this;
            openerp.jsonRpc("/get_sale_promotion", "call", {
                'sp_id': sp_id
            }).done(function(data){
                var content = openerp.qweb.render('sale_promotions_content', {
                    'sp_url': data['url'],
                    'sp_image': "background-image: url('" + data['image'] + "sale_promotions." + self.$target.attr("class") + "');",
                    //~ 'sp_name': data['name'],
                    //~ 'sp_description': data['description'],
                });
                self.$target.html(content);
            });
        }
    }
});


