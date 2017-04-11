var times = 0;

jQuery.fn.highlight = function (str, className) {
    var regex = new RegExp(str, "gi");
    return this.each(function () {
        $(this).contents().filter(function() {
            return this.nodeType == 3 && regex.test(this.nodeValue);
        }).replaceWith(function() {
            return (this.nodeValue || "").replace(regex, function(match) {
                return "<span class=\"" + className + "\">" + match + "</span>";
            });
        });
    });
};

$(document).ready(function(){

    if(typeof dermanord_kw !== 'undefined') {
        $(".fts_result *").highlight(dermanord_kw, "dn_highlight");
    }

    //~ var input_field = $("inupt[search]");
    //~ if(input_field.val().length == 0) {
        //~ $("#searchbox").find(".title_history").removeClass("hidden");
        //~ $("#searchbox").find(".result_history").removeClass("hidden");
        //~ $("#searchbox").find(".title_suggestion").addClass("hidden");
        //~ $("#searchbox").find(".result_suggestion").addClass("hidden");
        //~ $("#searchbox").find(".title_popular").removeClass("hidden");
        //~ $("#searchbox").find(".result_popular").removeClass("hidden");
    //~ }
    //~ else {
        //~ $("#searchbox").find(".title_history").addClass("hidden");
        //~ $("#searchbox").find(".result_history").addClass("hidden");
        //~ $("#searchbox").find(".title_suggestion").removeClass("hidden");
        //~ $("#searchbox").find(".result_suggestion").removeClass("hidden");
        //~ $("#searchbox").find(".title_popular").addClass("hidden");
        //~ $("#searchbox").find(".result_popular").addClass("hidden");
    //~ }

    //~ $(document).ready(function(){
        //~ $(".oe_select9_dn_search").select9();
    //~ });

});

$(window).scroll(function() {
    if($(window).scrollTop() == $(document).height() - $(window).height()) {
           // ajax call get data from server and append to the div
        console.log('bottom');
        $(".question").append();
        times ++;
    }
});
