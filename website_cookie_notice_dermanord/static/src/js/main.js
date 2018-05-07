$(document).ready(function() {
    if (Cookies.get("cookie_notification_accept") !== "1") {
        $("#website_cookie_notice").show();
    };
});

function cookie_notification_accept() {
        Cookies.set("cookie_notification_accept",  "1");
        $("#website_cookie_notice").hide();
    }
