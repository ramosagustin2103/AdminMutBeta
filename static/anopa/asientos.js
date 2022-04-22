$('#id_asiento-fecha_asiento').datepicker({
  format: "dd/mm/yyyy",
  autoclose: true,
  orientation: 'bottom auto',
  language: 'es'
});
$('input#id_asiento-descripcion').maxlength({
    alwaysShow: true,
    placement: 'top-left'
});

$('.cuenta, .debe, .haber').on( 'change', function() {
  var total_debe = 0;
  $('.debe').each(function(){
    if (this.value) {
      total_debe += parseFloat(this.value);
    }
  });
  var total_haber = 0;
  $('.haber').each(function(){
    if (this.value) {
      total_haber += parseFloat(this.value);
    }
  });

  $('#suma-debe').text(total_debe.toFixed(2));
  $('#suma-haber').text(total_haber.toFixed(2));


  if (total_debe.toFixed(2) == total_haber.toFixed(2)){
    $('#suma-debe, #suma-haber').removeClass('bg-danger').addClass('bg-success');
    $('#envio').attr("disabled", false);
  }
  else {
    $('#suma-debe, #suma-haber').removeClass('bg-success').addClass('bg-danger');
    $('#envio').attr("disabled", true);
  }
})