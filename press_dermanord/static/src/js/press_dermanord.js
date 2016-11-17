// .css_editable_mode_hidden: view mode
// .css_non_editable_mode_hidden: edit mode

$(".img_press_block").each(function () {
    var img_url = $(this).find(".img_2_change").attr("src");
    var id = img_url.substring(img_url.lastIndexOf("ir.attachment/")+14, img_url.lastIndexOf("_"));
    $(this).find(".img_press_website").attr("href", "/imagemagick/" + id + "/id/" + $(".website_recipe").attr("id"));
    $(this).find(".img_press_original").attr("href", "/imagemagick/" + id + "/id/" + $(".original_recipe").attr("id"));


    //~ var w = openerp.website.session.Model('website');
    //~ var res = w.call('get_id_from_url', [url], {});

    //~ .then(function (result) {
        //~ window.alert('hello');
    //~ }, function(r){ window.alert('ah');}
    //~ );
    //~ console.log(res);
    //~ openerp.jsonRpc("/crm/todo/create", 'call', {
        //~ 'partner': partner,
        //~ 'memo': $("input[name=memo]").val(),
    //~ }).done(function(data){
        //~ if(data == "note_created"){
            //~ $("#todo_table").load(document.URL + " #todo_table");
            //~ $("#note_memo").val("");
            //~ $("#note_button_group").addClass("hidden");
            //~ $("#show_note_button_group").removeClass("hidden");
        //~ }
    //~ });


});

