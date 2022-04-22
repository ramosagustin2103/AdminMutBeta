var total = Number(parseFloat($('.totales').text().replace(/\./g, "").replace(",", ".")));
var per_cap = Number(parseFloat($('.per_cap').text().replace(/\./g, "").replace(",", ".")));
var valor_cuenta_activo = Number(parseFloat($('.cuenta_activo').text().replace(/\./g, "").replace(",", ".")));
var valor_total_activo = Number(parseFloat($('.total_activo').text().replace(/\./g, "").replace(",", ".")));
var valor_cuenta_pn = Number(parseFloat($('.cuenta_pn').text().replace(/\./g, "").replace(",", ".")));
var valor_cuenta_resultados = Number(parseFloat($('.cuenta_resultados').text().replace(/\./g, "").replace(",", ".")));
var valor_total_pn = Number(parseFloat($('.total_pn').text().replace(/\./g, "").replace(",", ".")));
var valor_total_pasivo_pn = Number(parseFloat($('.total_pasivo_pn').text().replace(/\./g, "").replace(",", ".")));
var per_capita = $('.per_cap');
var cuenta_activo = $('.cuenta_activo');
var total_activo = $('.total_activo');
var cuenta_pn = $('.cuenta_pn');
var cuenta_resultados = $('.cuenta_resultados');
var total_pn = $('.total_pn');
var total_pasivo_pn = $('.total_pasivo_pn');
var reserva = $('.reserva');
$('input[name=per_cap_modelo]').val(per_cap);

$('#a_res_per_cap').on( 'change', function() {
  var coef = (total/per_cap).toFixed(0);
  var valor = Number($(this).val());
  if ($('#a_res_per_cap').val() != ''){
    $('#boton-envio').removeAttr("disabled");
    var a_reservar = valor * coef;
    var per_cap_final = per_cap+valor;
    reserva.html(a_reservar.toFixed(2).replace(".", ","));
    per_capita.html(per_cap_final.toFixed(2).replace(".", ","));
    cuenta_activo.html((valor_cuenta_activo+a_reservar+total).toFixed(2).replace(".", ","));
    total_activo.html((valor_total_activo+a_reservar+total).toFixed(2).replace(".", ","));
    cuenta_pn.html((valor_cuenta_pn-a_reservar).toFixed(2).replace(".", ","));
    cuenta_resultados.html((valor_cuenta_resultados-total).toFixed(2).replace(".", ","));
    total_pn.html((valor_total_pn-a_reservar-total).toFixed(2).replace(".", ","));
    total_pasivo_pn.html((valor_total_pasivo_pn-a_reservar-total).toFixed(2).replace(".", ","));

    $('input[name=a_reservar_modelo]').val(a_reservar);
    $('input[name=per_cap_modelo]').val(per_cap_final);
  }
  else{
    $('#boton-envio').attr("disabled", true);
    reserva.html("0,00");
    per_capita.html(per_cap.toFixed(2).replace(".", ","));
    cuenta_activo.html(valor_cuenta_activo.toFixed(2).replace(".", ","));
    total_activo.html(valor_total_activo.toFixed(2).replace(".", ","));
    cuenta_pn.html(valor_cuenta_pn.toFixed(2).replace(".", ","));
    total_pn.html(valor_total_pn.toFixed(2).replace(".", ","));
    total_pasivo_pn.html(valor_total_pasivo_pn.toFixed(2).replace(".", ","));
    $('input[name=a_reservar_modelo]').val(0);
    $('input[name=per_cap_modelo]').val(per_cap);
  }
});