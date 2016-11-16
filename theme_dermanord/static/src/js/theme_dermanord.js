function show_me(){
    // desktop size
    if ($(".collapse").is(":visible"))
        window.alert("desktop");
    // mobile size
    if (!$(".collapse").is(":visible"))
        window.alert("mobile");
}


