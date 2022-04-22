$('.credclass').on( 'change', function() {
  var valor = $(this).val();
  var final = 0.00;
  $('.credclass').each(function(){
    if( $(this).is(':checked') ) {
      var total_individual = $(this).closest('td').siblings('td.total_individual').text().replace(',','.');
      total_individual = parseFloat(total_individual);
      final = final + total_individual;
    }
  });

  var total_expensas = $('#total_expensas');
  total_expensas.html((final).toFixed(2));
  var total_comision = $('#total_comision');
  console.log("ad");
  var except = "1";
  if (except == "1") {
    var comision = 0.00;
  } else {
    var comision = ((final)*0.0569093).toFixed(2);
  }
  total_comision.html(comision);
  var total_final = $('#total_final');
  total_final.html((parseFloat(final)+parseFloat(comision)).toFixed(2));

  if( $(this).is(':checked') ) {
    $('#formExpensas').append("<input type='hidden' name='vinculo[]'' value=" + valor + ">");
  }
  else {
    $('input[type=hidden]').each(function(){
      if ($(this).val() === valor) {
        $(this).remove()
      }
    });
  };

  if (total_expensas.text() > 0.00) {
    $('#btn-pago').prop("disabled", false);
  }
  else{
    $('#btn-pago').prop("disabled", true);
  }
});