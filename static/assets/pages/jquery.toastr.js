$("#noModifica").click(function () {
    $.toast({
        heading: 'Accion denegada!',
        text: 'El objeto primario no se puede modificar. Solicite la accion al encargado de sistema.',
        position: 'top-right',
        loaderBg: '#bf441d',
        icon: 'error',
        hideAfter: 5000,
        stack: 1
    });
});