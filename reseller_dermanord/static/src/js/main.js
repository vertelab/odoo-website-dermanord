$(document).ready(function() {

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
