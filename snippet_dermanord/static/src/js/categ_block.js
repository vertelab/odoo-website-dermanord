$(document).ready(function() {
    $(".navbar-toggle").live(function(){
        if($(".navbar-toggle").is(":visible"))
            window.alert("wooah");
        }
    );
});
