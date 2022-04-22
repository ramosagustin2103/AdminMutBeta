$(window).load(function() {
  $(".se-pre-con").fadeOut("slow");;
});
$(function(){
  $('form').submit(function (e) {
      if ($(this).valid()) {
        $(".se-pre-con").show();
        return true;
      } else {
        e.preventDefault();
        return false;
      }
  });
});
$("form").attr('autocomplete', 'off');