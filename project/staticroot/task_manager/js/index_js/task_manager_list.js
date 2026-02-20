function getColumnIndexByHeader(headerText) {
    const headers = document.querySelectorAll(".tasks-list thead th");
    let columnIndex = 0;

    headers.forEach((header, index) => {
        if (header.textContent.trim() === headerText) {
            columnIndex = index;
        }
    });

    return columnIndex;
}

var TaskManagerList = function () {


    //
    // Setup components
    //

    // Datatable
    var _componentDatatable = function() {
        if (!$().DataTable) {
            console.warn('Warning - datatables.min.js is not loaded.');
            return;
        }

        // Initialize data table
        $('#tasks-list').dataTable({
            serverSide: true,
            autoWidth: false,

            ajax: {
                url: "http://127.0.0.1:8000/api/get/places/",
                data: function(d) {
                    d.sEcho = d.draw; // Добавляем sEcho, чтобы соответствовать старому API
                    d.iDisplayStart = d.start;
                    d.iDisplayLength = d.length;
                    d.iSortCol_0 = d.order[0].column;
                    d.sSortDir_0 = d.order[0].dir;
                    d.iSortingCols = d.order.length;
                    delete d.start;
                    delete d.length;
                    delete d.order;
                    delete d.draw;
                }
            },
            columns: [
                {name: "category", data: 0},
                {name: "name", data: 1},
                {name: "rating", data: 2},
                {name: "num_reviews", data: 3},
                {name: "country", data: 4},
                {name: "state", data: 5},
                {name: "city", data: 6},
                {name: "postcode", data: 7},
                {name: "place_type", data: 8,
                    render: function(data) {
                        return data ? data
                                    : '-';
                    }
                },
                {name: "phone", data: 9,
                    render: function(data) {
                        return data ? `<div class="text-center">
                                            <div class="text-success bg-success bg-opacity-25">
                                                Yes
                                            </div>
                                        </div>` 
                                    : `<div class="text-center">
                                            <div class="text-danger bg-danger bg-opacity-25">
                                                No
                                            </div>
                                        </div>`;
                    }
                },
                {name: "email", data: 10,
                    render: function(data) {
                        return data ? `<div class="text-center">
                                            <div class="text-success bg-success bg-opacity-25">
                                                Yes
                                            </div>
                                        </div>` 
                                    : `<div class="text-center">
                                            <div class="text-danger bg-danger bg-opacity-25">
                                                No
                                            </div>
                                        </div>`;
                    }
                },

                {name: "clear_website", data: 11,
                    render: function(data) {
                        return data ? `<div class="text-center">
                                            <a href="${data}">
                                                <i class="ph ph-link ph-lg"></i>
                                            </a>
                                        </div>` 
                                    : `<div class="text-center">-</div>`;
                    }
                },
                {name: "link", data: 12,
                    render: function(data) {
                        return `<a href="${data}"><i class="ph ph-info ph-lg"></i></a>`;
                    }
                },
            ],

            columnDefs: [
                {
                    targets: getColumnIndexByHeader("Category"),
                    width: "1%",
                },
                {
                    targets: getColumnIndexByHeader("Name"),
                    width: "2%",
                },
                {
                    targets: getColumnIndexByHeader("Rating"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Reviews"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Country"),
                    width: "0.4%",
                },
                {
                    targets: getColumnIndexByHeader("State"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("City"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Postcode"),
                    width: "0.1%",
                },  
                {
                    targets: getColumnIndexByHeader("Place type"),
                    width: "0.2%",
                },
                {
                    targets: getColumnIndexByHeader("Phone"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Email"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Website"),
                    width: "0.1%",
                },
                {
                    targets: getColumnIndexByHeader("Link"),
                    width: "0.1%",
                    orderable: false
                }
            ],

            dom: '<"datatable-header"fl><"datatable-scroll-lg"t><"datatable-footer"ip>',

            language: {
                search: '<span class="me-3">Search:</span> <div class="form-control-feedback form-control-feedback-end flex-fill">_INPUT_<div class="form-control-feedback-icon"><i class="ph-magnifying-glass opacity-50"></i></div></div>',
                searchPlaceholder: 'Type to search...',
                lengthMenu: '<span class="me-3">Show:</span> _MENU_',
                paginate: { 'first': 'First', 'last': 'Last', 'next': document.dir == "rtl" ? '&larr;' : '&rarr;', 'previous': document.dir == "rtl" ? '&rarr;' : '&larr;' }
            },
            lengthMenu: [15, 25, 50, 75, 100],
            displayLength: 25,
        });
    };


    //
    // Return objects assigned to module
    //

    return {
        init: function() {
            _componentDatatable();
        }
    }
}();


// Initialize module
// ------------------------------

document.addEventListener('DOMContentLoaded', function() {
    TaskManagerList.init();
});