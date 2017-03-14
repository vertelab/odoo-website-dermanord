(function () {
    'use strict';

    var website = openerp.website;
    
    
    
    website.snippet.options.dermanord_experience = website.snippet.Option.extend({
        //~ dermatest: function () {
            
        //~ }
    });
    
    $(document).ready(function() {
        $(".show_more_block").click(function() {
            $("#show_less_block").removeClass("hidden");
            $("#show_more_block").addClass("hidden");
            $.each($(".categ_p_section").find(".extra_block"), function(){
                $(this).removeClass("hidden-xs");
            });
        });
    });

})();
