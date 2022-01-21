// Call the dataTables jQuery plugin



$(document).ready(function() {
  $('#dataTable').DataTable(
  {
        "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]]
      
  }
  );
});
