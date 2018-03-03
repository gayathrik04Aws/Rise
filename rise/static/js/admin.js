var planUpdated = false;

////
//// Flight surcharge input
$('.flight-surcharge-checkbox').change(function(){
    var nearestParent = $(this).parentsUntil('.flight-type');
    if ($(this).is(':checked')) {
        nearestParent.addClass('flight-type-selected');
        $('.surcharge').toggle();
    } else {
        nearestParent.removeClass('flight-type-selected');
        $('.surcharge').toggle();
    }
});



////
//// Account type fieldsets
function accountTypeSelect() {
    var accountSelect = $('#id_account_type').val();

    if (accountSelect === 'I') {
        $('fieldset#individual_account_type').show();
        $('fieldset#corporate_account_type').hide();
    } else if(accountSelect === 'C') {
        $('fieldset#corporate_account_type').show();
        $('fieldset#individual_account_type').hide();
    }
}

$(function() {
    accountTypeSelect();

    $('#id_account_type').change(function(){
        accountTypeSelect();
    });

    // calculateCorporateAmount();
});
$('.change-background-check-status').change(function(){
    var form = this.form;
    url = $(form).attr('action');
    data = $(form).serialize();

    $.ajax({
        type: 'POST',
        url: url,
        data: data,
        dataType: 'json',
        success: function(data) {
            if ('success' in data){
                var successMessage = 'The passenger status has been updated.';
                displayMessage(successMessage);
            }
            else if ('error' in data){
                displayMessage('Error: ' + data.error);
            }
        },
        error: function(data){
            var errorMessage = 'There was an error updating the passenger status. Please stand by.';
            displayMessage(errorMessage);
        }
    });
});
$('.check_in_passenger').change(function(){
    var this_input = $(this);
    var form = this.form;
    url = $(form).attr('action');
    data = $(form).serialize();

    $.ajax({
        type: 'POST',
        url: url,
        data: data,
        dataType: 'json',
        success: function(data) {
            if ('success' in data){
                //var successMessage = 'The passenger status has been updated.';
                //displayMessage(successMessage);
                //$(this_input).prop('disabled', true);
            }
            else if ('error' in data){
                displayMessage('Error: ' + data.error);
            }
        },
        error: function(data){
            var errorMessage = 'There was an error updating the passenger status. Please stand by.';
            displayMessage(errorMessage);
        }
    });
});

$('#id_corporate_amount').change(function(){
    planUpdated = true;
});

function calculateCorporateAmount(){
    var baseCost = 3700,
        saveMySeatCost = 925,
        depositCost = 750,
        passThreshold = 4;

    $members = $('#id_member_count');
    $passes = $('#id_pass_count');
    $corporateAmount = $('#id_corporate_amount');

    if ($members.length && $passes.length && $corporateAmount.length){
        calculatedValue = baseCost + parseInt($passes.val() - passThreshold) * saveMySeatCost;
        $corporateAmount.val(calculatedValue);
    }

}

// same as in profile.js - trying to separate out js file functionality if not needed
function displayMessage(message){
    var $message = $('<div class="modal-wrapper" style="display: block; z-index: 10000; opacity: 1;"><div class="modal center"><figure class="x-grey-lg"></figure><figure class="alert-icon"></figure><p class="thick">'+message+'</p><a href="" class="dismiss action-block grey condensed">Okay, got it<figure class="arrow-right-grey"></figure></a></div></div>');
    $('body').prepend($message);
    $('.x-grey-lg').on(clickAction, function(e) {
        e.preventDefault();
        location.reload();
    });
}

////
//// On Dekstop, click events will be 'click', on Mobile, 'tap'
var clickAction = (isMobile.any()) ? 'tap' : 'click';

////
//// Add another corporation input to new flight

$(document).ready(function(){
    var max_inputs = 10;
    var x = 1;

    $('.add-corporation-button').on(clickAction, function(e){
        if(x < max_inputs){
            x++;
            $('.add-corporations').append('<input id="allowed_corporations{{ forloop.counter }}" type="text" name="{{ form.allowed_corporations.name }}">');
        }
    });


    //force_margin_relative_to_height('nav.rise-admin .rise-admin-wrapper','.admin-content-wrap',100);
});

function force_margin_relative_to_height(the_height_element, the_relative_element, the_vertical_offset) {
    if ( $(the_height_element).length > 0 && $(the_relative_element).length > 0 ) {
        var height_element = the_height_element;
        var height_in_pixels = $(height_element).outerHeight();
        var relative_element = the_relative_element;

        $(relative_element).css('margin-top',(height_in_pixels+the_vertical_offset)+'px');

        $(window).resize(function() {
            height_in_pixels = $(height_element).outerHeight();
            $(relative_element).css('margin-top',(height_in_pixels+the_vertical_offset)+'px');
        });

        return true;
    }
    else {
        return false;
    }
}

var $idFilter = $('#id_filter_user');
$('.filter').on(clickAction, function(){
    filter_value = $(this).attr('data-filter');
    select_value = $(this).html().trim();
    $idFilter.val(filter_value);
    $('#flight-sort-filter').prev().html(select_value);
    $('#flight-sort-filter, .admin-page-sort').removeClass('expand');
    updateUserFilter(filter_value);
});

$idFilter.change(function(){
    filter_value = $(this).val();
    $('.filter.ui-selected').removeClass('ui-selected');
    $('.filter[data-filter="'+filter_value+'"]').addClass('ui-selected');
    updateUserFilter(filter_value);
});

function updateUserFilter(filter_value){
    $("#flight-sort-filter li.active").removeClass('active');
    $('#flight-sort-filter li[value="'+filter_value+'"]').addClass('active');
    $('.filter.ui-selected').removeClass('ui-selected');
    $('.filter[data-filter="'+filter_value+'"]').addClass('ui-selected');

    filter_value = filter_value.trim();

    if (filter_value){
        var filter_list = filter_value.split('|');
        $('.user-row.fadeIn').removeClass('fadeIn');
        $('.user-row').addClass('fadeOut');
        for (var i = 0; i < filter_list.length; i++){
            var character = filter_list[i];
            $('.user-row[data-last-name^="'+character+'"]').removeClass('fadeOut').addClass('fadeIn');
        }
    }
    else{
        $('.user-row.fadeOut').removeClass('fadeOut');
        $('.user-row').addClass('fadeIn');
    }
}

$('#id_filter_waitlist').change(function(){
    flight = $(this).val();
    if (flight){
        $('.waitlist-item.fadeIn').removeClass('fadeIn');
        $('.waitlist-item').addClass('fadeOut');
        $('.waitlist-item[data-flight="'+flight+'"]').removeClass('fadeOut').addClass('fadeIn');
    }
    else{
        $('.waitlist-item').removeClass('fadeOut').addClass('fadeIn');
    }
});

////
//// confirmation for account plan changes
$('#admin-save-account').on('click clickAction', function(e){
    if (planUpdated){
        e.preventDefault();
        $('#plan_change_modal').show();
        return false;
    }
});

$('#confirm_plan_change').on('click clickAction', function(e){
    e.preventDefault();
    $('#account-edit').submit();
    return false;
});


$(function() {
    $('#merge_account_modal_button').on(clickAction, function(event) {
        event.preventDefault();
        $('#merge_modal').show();
    });

    $('#merge_corporate_account').on(clickAction, function(event) {
        event.preventDefault();
        var corporateAccountSelect = $('#id_corporate_account'),
            corporateAccountId = corporateAccountSelect.val(),
            url = corporateAccountSelect.data('url');

        $.ajax({
            type: 'POST',
            url: url,
            data: {account_id: corporateAccountId},
            dataType: 'json',
            success: function(data) {
                $('#merge_modal').hide();
                $('#corporate_account_link').attr('href', '/riseadmin/accounts/' + corporateAccountId + '/');
                $('#merge_success_modal').show();
            },
            error: function(data){
                var errorMessage = 'There was an error merging accounts';

                if (data.error) {
                    errorMessage = data.error;
                }

                displayMessage(errorMessage);
            }
        });
    });
});


$( ".unconfirmed_button" ).on(clickAction, function(e){
    var currentFlight = $(this);
    var seats =  currentFlight.data("seats");
    var totalseats =  currentFlight.data("totalseats");
    if( seats < totalseats ) {
        e.preventDefault();
        var message = "This flight only has " + seats + " out of " + totalseats + " seats booked.  Are you SURE you wish to confirm this flight?";
        confirmModal(message, currentFlight);
    }

});


function confirmModal(message,currentFlight){
    var $message = $('<div class="modal-wrapper" style="display: block; z-index: 10000; opacity: 1;"><div class="modal center"><figure class="x-grey-lg"></figure><figure class="alert-icon"></figure><p class="thick">'+message+'</p><a href="javascript:void(0);" class="continue-flight action-block grey condensed">Continue?<figure class="arrow-right-grey"></figure></a></div></div>');
    $('body').prepend($message);
    $('.x-grey-lg').on(clickAction, function(e) {
        e.preventDefault();
        $("body").find(".modal-wrapper").remove();

    });
    $('.continue-flight').on(clickAction, function(e) {
        currentFlight.parent("form").submit();
    });

}
