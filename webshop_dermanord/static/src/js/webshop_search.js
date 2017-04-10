$(document).ready(function(){

    $(".fts_result").find("h3, h4, h5, span").each(function(){
        console.log($(this).text());
        if($(this).text().toLowerCase().indexOf(dermanord_kw) > -1){
            content = $(this).text();
            content_arr = content.split(dermanord_kw); //TODO: case insensitve on regex
            $(this).html(content_arr[0] + "<span class='dn_kw'>" + dermanord_kw + "</span>" + content_arr[1]);
        }
    });

    $(document).ready(function(){
        $(".oe_select9_dn_search").select9();
    });

});

$(window).scroll(function() {
    if($(window).scrollTop() == $(document).height() - $(window).height()) {
           // ajax call get data from server and append to the div
        console.log('bottom');
    }
});
