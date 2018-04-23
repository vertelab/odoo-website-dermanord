$(document).ready(function(){
    $("i#remove_img").click(function(){
        var self = $(this);
        openerp.jsonRpc("/reseller_register/remove_img", "call", {
            'partner_id': self.data("partner_id")
        }).done(function(data){
            if (data) {
                $("img#top_image_show").attr("src", "");
                self.find("input").val('1');
                self.addClass("hidden");
            }
        });
    });
});
