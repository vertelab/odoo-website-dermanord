// .css_editable_mode_hidden: view mode
// .css_non_editable_mode_hidden: edit mode
$('.img_press_block').each(function () {
    var url = $(this).find('.css_editable_mode_hidden').attr('src');
    var w = openerp.website.session.Model('website');
    var res = w.call('get_id_from_url', [url], {});

    //~ .then(function (result) {
        //~ window.alert('hello');
    //~ }, function(r){ window.alert('ah');}
    //~ );
    console.log(res);
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

