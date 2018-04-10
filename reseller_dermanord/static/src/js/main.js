$(document).ready(function() {
    if ($("#reseller_description_div").height() > 300) {
        $("#reseller_description_div").height(300);
        $("#reseller_description_div").find(".read-more").removeClass("hidden");
    }
    $("i#remove_img").click(function(){
        $("img#top_image_show").attr("src", "");
        $(this).find("input").val('1');
        $(this).addClass("hidden");
    });
    d = new Date();
    $("#myimg").attr("src", "/myimg.jpg?"+d.getTime());
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


var $el, $ps, $up, totalHeight;

$("#reseller_description_div .button").click(function() {

  totalHeight = 0

  $el = $(this);
  $p  = $el.parent();
  $up = $p.parent();
  $ps = $up.find("p:not('.read-more')");

  // measure how tall inside should be by adding together heights of all inside paragraphs (except read-more paragraph)
  $ps.each(function() {
    totalHeight += $(this).outerHeight() + 10; // 10px from each p-tag
  });

  console.log(totalHeight);

  $up
    .css({
      // Set height to prevent instant jumpdown when max height is removed
      "height": $up.height(),
      "max-height": 9999
    })
    .animate({
      "height": totalHeight
    });

  // fade out read-more
  $p.fadeOut();

  // prevent jump-down
  return false;

});
