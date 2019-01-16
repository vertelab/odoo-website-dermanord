$(document).ready(function() {
    //~ if ($("#reseller_description_div").height() > 300) {
        //~ $("#reseller_description_div").height(300);
        //~ $("#reseller_description_div").find(".read-more").removeClass("hidden");
    //~ }
    $("i#remove_img").click(function(){
        var self = $(this);
        openerp.jsonRpc("/remove_img", "call", {
            'partner_id': self.data("partner_id")
        }).done(function(data){
            if (data) {
                $("img#top_image_show").attr("src", "");
                self.find("input").val('1');
                self.addClass("hidden");
            }
        });
    });
    getLocation();
    getClientIP();
});

function reseller_restore_filter() {
    $("#dn_reseller_filter_modal").find(".modal-body").find("input[type=checkbox]").each(
        function() {
            if($(this).is(":checked")) {
                $(this).removeAttr('checked');
            }
        }
    );
}

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(setPosition);
    }
}
function setPosition(position) {
    $("input#pos_lng").val(position.coords.longitude);
    $("input#pos_lat").val(position.coords.latitude);
}
function getClientIP() {
    $.getJSON("https://ipapi.co/json/", function(data) {
        $("input#client_ip").val(data['ip']);
    });
}

//~ var $el, $ps, $up, totalHeight;

//~ $("#reseller_description_div .button").click(function() {

  //~ totalHeight = 0

  //~ $el = $(this);
  //~ $p  = $el.parent();
  //~ $up = $p.parent();
  //~ $ps = $up.find("p:not('.read-more')");

  //~ // measure how tall inside should be by adding together heights of all inside paragraphs (except read-more paragraph)
  //~ $ps.each(function() {
    //~ totalHeight += $(this).outerHeight() + 10; // 10px from each p-tag
  //~ });

  //~ $up
    //~ .css({
      //~ // Set height to prevent instant jumpdown when max height is removed
      //~ "height": $up.height(),
      //~ "max-height": 9999
    //~ })
    //~ .animate({
      //~ "height": totalHeight
    //~ });

  //~ // fade out read-more
  //~ $p.fadeOut();

  //~ // prevent jump-down
  //~ return false;

//~ });
