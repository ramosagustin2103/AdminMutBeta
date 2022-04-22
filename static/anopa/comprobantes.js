$('.credclass').on( 'change', function() {
  var valor = $(this).val();
  var final = 0.00;
  $('.credclass').each(function(){
    var valor = $(this).val();
    if( $(this).is(':checked') ) {
      var total_individual = $(this).closest('td').siblings('td.total_individual').text().replace(',','.');
      total_individual = parseFloat(total_individual);
      final = final + total_individual;
    }
  });

  var subtotal = $('#subtotal');
  subtotal.text((final).toFixed(2));
  
  if( $(this).is(':checked') ) {
    $('#formComprobante').append("<input type='hidden' name='vinculo[]'' value=" + valor + ">");
  } 
  else {
    $('input[type=hidden]').each(function(){
      if ($(this).val() === valor) {
        $(this).remove()
      }
    });
  }
});