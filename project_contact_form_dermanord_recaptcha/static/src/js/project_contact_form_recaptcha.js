function enable_send_button (){
    $("button[class='btn btn-primary btn-lg']").prop("disabled",false)
    console.log("Send button enabled")
}
function disable_send_button (){
    $("button[class='btn btn-primary btn-lg']").prop("disabled",true)
    console.log("Send button enabled")
}

// Disable and set enable as reCAPTCHA callback: data-callback
disable_send_button()
