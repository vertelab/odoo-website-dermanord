$(document).ready(function(){
    'use strict';
    $("input[name=search]").keyup(function(event){
        if (event.which == 13) {
            $(this).parents('form').submit()
        } else if ($(this).val().trim().length > 2) {
            odoo.jsonRpc("/search_suggestion", "call", {
                search: $(this).val(),
                res_model: ['product.template', 'product.product', 'product.public.category', 'blog.post'], //, 'product.facet.line'],
                limit: 15, // [2554] Webbshop - Utöka antal sökträffar i toppsökning
                offset: 0
            }).done(function(data){
                //~ var content_front = '<div class="result_suggestion">';
                //~ var content_behind = '</div>';
                //~ var content = '';
                let content = $('<div class="result_suggestion">');
                
                $.each(data, function(key, info) {
                    let li = $('<li>');
                    let a = $('<a>');
                    let img = $('<img>');
                    li.append(a);
                    li.append(img);
                    a.text(data[key]['name']);
                    a.prepend(img);
                    if (data[key]['model_record'] == 'product.template'){
                        img.attr('src', '/imagefield/product.template/image_small/' + data[key]['res_id'] + '/ref/webshop_dermanord.fts_image');
                        if (data[key]['event_type_id']){
                            a.attr('href', '/event/type/' + data[key]['event_type_id']);
                            //~ var c = '<li><a href="/event/type/' + data[key]['event_type_id'] + '"><img src="/imagefield/product.template/image_small/' + data[key]['res_id'] + '/ref/website_imagemagick.fts_image' + '">' + data[key]['name'] + '</a></li>';
                            //~ var c = '<li><a href="/event/type/' + data[key]['event_type_id'] + '">' + data[key]['name'] + '</a></li>';
                        } else {
                            a.attr('href', '/dn_shop/product/' + data[key]['res_id']);
                            //~ img.attr('src', '/imagefield/product.template/image_small/' + data[key]['res_id'] + '/ref/website_imagemagick.fts_image');
                            //~ var c = '<li><a href="/dn_shop/product/' + data[key]['res_id'] + '"><img src="/imagefield/product.template/image_small/' + data[key]['res_id'] + '/ref/website_imagemagick.fts_image' + '">' + data[key]['name'] + '</a></li>';
                            //var c = '<li><a href="/dn_shop/product/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        }
                        content.append(li);
                    }
                    else if (data[key]['model_record'] == 'product.product'){
                        img.attr('src', '/imagefield/product.product/image_small/' + data[key]['res_id'] + '/ref/webshop_dermanord.fts_image');
                        if (data[key]['event_type_id']){
                            a.attr('href', '/event/type/' + data[key]['event_type_id']);
                            //~ var c = '<li><a href="/event/type/' + data[key]['event_type_id'] + '">' + data[key]['name'] + '</a></li>';
                        } else {
                            a.attr('href', '/dn_shop/variant/' + data[key]['res_id']);
                            //~ var c = '<li><a href="/dn_shop/variant/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        }
                        content.append(li);
                    }
                    else if (data[key]['model_record'] == 'product.public.category'){
                        img.attr('src', '/imagefield/product.public.category/image_small/' + data[key]['res_id'] + '/ref/webshop_dermanord.fts_image');
                        a.attr('href', '/webshop/category/' + data[key]['res_id']);
                        //~ var c = '<li><a href="/webshop/category/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        content.append(li);
                    }
                    else if (data[key]['model_record'] == 'blog.post'){
                        if (data[key]['image_attachment_id']) {
                            img.attr('src', '/imagefield/ir.attachment/datas/' + data[key]['image_attachment_id'] + '/ref/webshop_dermanord.fts_image');
                        }
                        a.attr('href', '/blog/' + data[key]['blog_id'] + '/post/' + data[key]['res_id']);
                        //~ var c = '<li><a href="/blog/' + data[key]['blog_id'] + '/post/' + data[key]['res_id'] + '">' + data[key]['name'] + '</a></li>';
                        content.append(li);
                    }
                    else if (data[key]['model_record'] == 'product.facet.line'){
                        img.attr('src', '/imagefield/product.facet.line/image_small/' + data[key]['res_id'] + '/ref/webshop_dermanord.fts_image');
                        a.attr('href', '/dn_shop/product/' + data[key]['product_tmpl_id'] + + data[key]['product_name']);
                        //~ var c = '<li><a href="/dn_shop/product/' + data[key]['product_tmpl_id'] + '">' + data[key]['product_name'] + '</a></li>';
                        content.append(li);
                    }
                });
                $(".result_suggestion").replaceWith(content)
                //~ $(".result_suggestion").html(content_front + content + content_behind)
            });
        }
    });
});
