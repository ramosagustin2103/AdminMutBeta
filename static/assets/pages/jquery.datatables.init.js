/**
 * Theme: Adminox Admin Template
 * Author: Coderthemes
 * Component: Datatable
 * 
 */
var handleDataTableButtons = function() {
        "use strict";
        0 !== $("#anopa").length && $("#anopa").DataTable({
            dom: "Bfrtip",
            buttons: [{
                extend: "excel",
                className: "btn-sm"
            }, {
                extend: "print",
                className: "btn-sm"
            }],
            responsive: !0,
            ordering: false,
        })
    },
    TableManageButtons = function() {
        "use strict";
        return {
            init: function() {
                handleDataTableButtons()
            }
        }
    }();