$(document).ready(function(){
    'use strict';
    $("input[name=search]").keyup(function(event){
        if (event.which == 13) {
            $(this).parents('form').submit()
        } else if ($(this).val().trim().length > 2) {
            openerp.jsonRpc("/search_suggestion", "call", {
                search: $(this).val(),
                res_model: ['product.template', 'product.product', 'product.public.category'], //, 'product.facet.line'],
                limit: 5,
                offset: 0
            }).done(function(data){
                var content_front = '<div class="result_suggestion">';
                var content_behind = '</div>';
                var content = '';
                $.each(data, function(key, info) {
                    if (data[key]['model_record'] == 'product.template'){
                        if (data[key]['event_type_id']){
                            var c = '<li><a href="/event/type/' + data[key]['event_type_id'] + '">' + data[key]['name'] + '</a></li>';
                        } else {
                            var c = '<li><a href="/dn_shop/product/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        }
                        content += c;
                    }
                    else if (data[key]['model_record'] == 'product.product'){
                        if (data[key]['event_type_id']){
                            var c = '<li><a href="/event/type/' + data[key]['event_type_id'] + '">' + data[key]['name'] + '</a></li>';
                        } else {
                            var c = '<li><a href="/dn_shop/variant/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        }
                        content += c;
                    }
                    else if (data[key]['model_record'] == 'product.public.category'){
                        var c = '<li><a href="/webshop/category/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        content += c;
                    }
                    else if (data[key]['model_record'] == 'blog.post'){
                        var c = '<li><a href="/blog/' + data[key]['blog_id'] + '/post/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        content += c;
                    }
                    else if (data[key]['model_record'] == 'product.facet.line'){
                        var c = '<li><a href="/dn_shop/product/' + data[key]['product_tmpl_id'] + '">' + data[key]['product_name'] + '</a></li>';
                        content += c;
                    }
                });
                $(".result_suggestion").html(content_front + content + content_behind)
            });
        }
    });
});
