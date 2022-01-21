// Call the dataTables jQuery plugin

// known issue: if the table is paginated and the last page has only 10 or less entries it's hiding the pagination
// so we can't come back.

$(document).ready(function() {
  $('#dataTable').DataTable(
  {
        "lengthMenu": [[ 25, 50, -1], [ 25, 50, "All"]],
        "order": [[ 0, "desc" ]],
       "fnDrawCallback": function(oSettings) {
        if ($('#dataTable tr').length < 11) {
            $('.dataTables_paginate').hide();
        }
    }
  }
  );
  
});


