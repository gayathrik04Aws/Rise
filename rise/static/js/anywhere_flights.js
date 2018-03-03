/**
 * Created by anye on 1/27/16.
 */
function getAvailableAnywhereFlights(url){
    $.get(url,{},function(data){
        var table = $('#flightset_table');
        if (table == null){
            table = $("#available-flights");
        }
        if (table == null) return false;
        $(table).html(data);
    });
}

function explainCostEstimate(){
    var modal = $('#cost_estimate_modal');
    if (modal != null){
        modal.show();
    }
}
