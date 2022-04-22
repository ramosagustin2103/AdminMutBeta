$('.gastoclass, .deudclass').on( 'change', function() {
  var final = 0.00;
  $('.deudclass').each(function(){
    var valor = $(this).val();
    if( $(this).is(':checked') ) {
      var total_individual = $(this).closest('td').siblings('td.total_individual').text().replace(',','.');
      total_individual = parseFloat(total_individual);
      final = final + total_individual;
    }
  });
  $('.gastoclass').each(function(){
    var valor = $(this).val();
    if (valor === ""){
      valor = 0.00;
    }
    final = final + parseFloat(valor);
  });

  var total = $('#total');
  total.text((final).toFixed(2));
});
$('.deudclass').on( 'change', function() {
  var valor = $(this).val();
  if( $(this).is(':checked') ) {
    $('#formOP').append("<input type='hidden' name='vinculo[]'' value=" + valor + ">");
  }
  else {
    $('input[type=hidden]').each(function(){
      if ($(this).val() === valor) {
        $(this).remove()
      }
    });
  }
});
