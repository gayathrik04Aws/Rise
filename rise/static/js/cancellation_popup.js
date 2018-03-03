/**
 * Created by anye on 5/3/16.
 */

$('#anywhere_form').submit(function(event) {
        $('#cancel_policy_modal').show();
        return false;
});

function submitForm(){
    var $form=$('#anywhere_form');
    $("#confirm_policy").attr("disabled", "disabled");
    $('#confirm_policy').removeAttr("href");
    $('#anywhere_form').get(0).submit();
}
function closeCancellationModal(){
    $('#cancel_policy_modal').hide();
}
