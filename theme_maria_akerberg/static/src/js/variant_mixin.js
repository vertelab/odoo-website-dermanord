odoo.define('theme_maria_akerberg.VariantMixin', function (require) {
    "use strict";


    require('web.dom_ready');
    const ajax = require('web.ajax');
    const VariantMixin = require('sale.VariantMixin');
    // const WebsiteSale = require('website_sale');
    var publicWidget = require('web.public.widget');

    // console.log(WebsiteSale)

    // publicWidget.registry.WebsiteSale = publicWidget.Widget.extend(WebsiteSale, {
    publicWidget.registry.WebsiteSale = publicWidget.Widget.extend(VariantMixin, {

        _updateProductImage: function ($productContainer, displayImage, productId, productTemplateId, newCarousel, isCombinationPossible) {
            var $carousel = $productContainer.find('#o-carousel-product');
            console.log('kdkkdkd')
            // When using the web editor, don't reload this or the images won't
            // be able to be edited depending on if this is done loading before
            // or after the editor is ready.
            if (window.location.search.indexOf('enable_editor') === -1) {
                var $newCarousel = $(newCarousel);
                $carousel.after($newCarousel);
                $carousel.remove();
                $carousel = $newCarousel;
                $carousel.carousel(0);
                this._startZoom();
                // fix issue with carousel height
                this.trigger_up('widgets_start_request', {$target: $carousel});
            }
            $carousel.toggleClass('css_not_available', !isCombinationPossible);
    },

    });


    // VariantMixin.extend({
    //     _onChangeCombination: function (ev, $parent, combination) {
    //         var self = this;
    //         var $price = $parent.find(".oe_price:first .oe_currency_value");
    //         var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
    //         var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
    //         $price.text(self._priceToStr(combination.price));
    //         $default_price.text(self._priceToStr(combination.list_price));
    //
    //         var isCombinationPossible = true;
    //         if (!_.isUndefined(combination.is_combination_possible)) {
    //             isCombinationPossible = combination.is_combination_possible;
    //         }
    //         this._toggleDisable($parent, isCombinationPossible);
    //
    //         if (combination.has_discounted_price) {
    //             $default_price
    //                 .closest('.oe_website_sale')
    //                 .addClass("discount");
    //             $optional_price
    //                 .closest('.oe_optional')
    //                 .removeClass('d-none')
    //                 .css('text-decoration', 'line-through');
    //             $default_price.parent().removeClass('d-none');
    //         } else {
    //             $default_price
    //                 .closest('.oe_website_sale')
    //                 .removeClass("discount");
    //             $optional_price.closest('.oe_optional').addClass('d-none');
    //             $default_price.parent().addClass('d-none');
    //         }
    //
    //         var rootComponentSelectors = [
    //             'tr.js_product',
    //             '.oe_website_sale',
    //             '.o_product_configurator'
    //         ];
    //
    //         // update images only when changing product
    //         // or when either ids are 'false', meaning dynamic products.
    //         // Dynamic products don't have images BUT they may have invalid
    //         // combinations that need to disable the image.
    //         if (!combination.product_id ||
    //             !this.last_product_id ||
    //             combination.product_id !== this.last_product_id) {
    //             this.last_product_id = combination.product_id;
    //             self._updateProductImage(
    //                 $parent.closest(rootComponentSelectors.join(', ')),
    //                 combination.display_image,
    //                 combination.product_id,
    //                 combination.product_template_id,
    //                 combination.carousel,
    //                 isCombinationPossible
    //             );
    //
    //             self._updateProductVariantImage(
    //                 $parent.closest(rootComponentSelectors.join(', ')),
    //                 combination.display_image,
    //                 combination.product_id,
    //                 combination.product_template_id,
    //                 combination.carousel,
    //                 isCombinationPossible
    //             )
    //         }
    //
    //         $parent
    //             .find('.product_id')
    //             .first()
    //             .val(combination.product_id || 0)
    //             .trigger('change');
    //
    //         $parent
    //             .find('.product_display_name')
    //             .first()
    //             .text(combination.display_name);
    //
    //         $parent
    //             .find('.js_raw_price')
    //             .first()
    //             .text(combination.price)
    //             .trigger('change');
    //
    //         this.handleCustomValues($(ev.target));
    //     },
    //
    //     _updateProductVariantImage: function ($productContainer, displayImage, productId, productTemplateId) {
    //         var model = productId ? 'product.product' : 'product.template';
    //         var modelId = productId || productTemplateId;
    //         var imageUrl = '/web/image/{0}/{1}/' + (this._productImageField ? this._productImageField : 'image_1024');
    //         var imageSrc = imageUrl
    //             .replace("{0}", model)
    //             .replace("{1}", modelId);
    //
    //         var imagesSelectors = [
    //             'span[data-oe-model^="product."][data-oe-type="image"] img:first',
    //             'img.product_detail_img',
    //             'span.variant_image img',
    //             'img.variant_image',
    //         ];
    //
    //         var $img = $productContainer.find(imagesSelectors.join(', '));
    //
    //         if (displayImage) {
    //             $img.removeClass('invisible').attr('src', imageSrc);
    //         } else {
    //             $img.addClass('invisible');
    //         }
    //     },
    //
    // })

});
