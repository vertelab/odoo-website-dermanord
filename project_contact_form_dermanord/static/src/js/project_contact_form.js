$(document).ready(function() {});

$("#selectedCase").change(function() {
  $(this)
    .find("option:selected")
    .each(function() {
      let project_id = $(this).val();
      if (project_id) {
        $(".dermanord-case")
          .not("#dermanord-case-" + project_id)
          .addClass("hidden");
        $("#dermanord-case-" + project_id).removeClass("hidden");
      } else {
        $(".dermanord-case").addClass("hidden");
      }
    });
});
