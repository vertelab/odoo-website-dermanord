COPY product_public_category                       TO '/tmp/product_public_category.sql';
COPY product_public_category_product_template_rel  TO '/tmp/product_public_category_product_template_rel.sql';
COPY product_public_category_res_groups_rel        TO '/tmp/product_public_category_res_groups_rel.sql';
COPY product_public_category_res_partner_category_rel TO '/tmp/product_public_category_res_partner_category_rel.sql';
COPY product_public_category_res_partner_rel       TO '/tmp/product_public_category_res_partner_rel.sql';
COPY product_facet_product_public_category_rel     TO '/tmp/product_facet_product_public_category_rel.sql';
COPY blog_post_product_public_category_rel         TO '/tmp/blog_post_product_public_category_rel.sql';



COPY product_public_category                       FROM '/tmp/product_public_category.sql';
COPY product_public_category_product_template_rel  FROM '/tmp/product_public_category_product_template_rel.sql';
COPY product_public_category_res_groups_rel        FROM '/tmp/product_public_category_res_groups_rel.sql';
COPY product_public_category_res_partner_category_rel FROM '/tmp/product_public_category_res_partner_category_rel.sql';
COPY product_public_category_res_partner_rel       FROM '/tmp/product_public_category_res_partner_rel.sql';
COPY product_facet_product_public_category_rel     FROM '/tmp/product_facet_product_public_category_rel.sql';
COPY blog_post_product_public_category_rel         FROM '/tmp/blog_post_product_public_category_rel.sql';

# show on start page !!!