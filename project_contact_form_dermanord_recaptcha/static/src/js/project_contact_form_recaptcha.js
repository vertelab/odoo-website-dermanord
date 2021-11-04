function enable_send_button (){
    $("button[class='btn btn-primary btn-lg']").prop("disabled",false)
    console.log("Send button enabled")
}
function disable_send_button (){
    $("button[class='btn btn-primary btn-lg']").prop("disabled",true)
    console.log("Send button disabled")
}

/**
 * Shamelessly taken from website_form_recaptcha/src/js/field_recaptcha.js
 * WARNING: This makes it hard to extend the functionality of the reCAPTCHA
 * module.
 */
(function ($) {
  "use strict";
  openerp.website.snippet.animationRegistry.form_recaptcha
  = openerp.website.snippet.Animation.extend({
    selector: ".o_website_form_recaptcha",
    start: function() {
      var self = this;
      this._super();
      $.ajax({
        url: '/website/recaptcha/',
        method: 'GET',
        success: function(data){
          data = JSON.parse(data);
          self.$target.append($(
            '<div class="g-recaptcha" data-sitekey="' + data.site_key + '" data-callback="enable_send_button" data-expired-callback="disable_send_button"></div>'
          ));
          $.getScript('https://www.google.com/recaptcha/api.js');
        },
      });
    }

  });

})(jQuery);

// Disable and set enable as reCAPTCHA callback: data-callback
disable_send_button()
