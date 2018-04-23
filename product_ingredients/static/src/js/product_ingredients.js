$(document).ready(function () {
    openerp.website.add_template_file('/product_ingredients/static/src/xml/templates.xml');
    $('.ingredient_slide').each(function (index, element)
    {
        element = $(element);
        console.log(element);
        product_id = element.data('product');
        openerp.jsonRpc("/product_ingredients/get_ingredients/" + product_id, "call", {}).done(function (data) {
            console.log(data);
            var indicator_content = '';
            var ingredients_content = '';
            for (i = 0; i < data.length; i++) {
                var i_content = openerp.qweb.render('ingredient_slide_indicators', {
                        'indicator': i == 0 ? "active" : "",
                        'slide_nr': i,
                    });
                var content = openerp.qweb.render('blog_slide_content', data[i]);
                indicator_content += i_content;
                ingredients_content += content;
            };
            element.find(".ingredient_slide_indicators").html(indicator_content);
            element.find(".ingredient_slide_content").html(blog_content);
        });
    });
});




