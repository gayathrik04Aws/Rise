var secondsRemaining = -1;

var timeRemaining = function() {
    $.get('/book/remaining/', function(data) {
        secondsRemaining = data.total_seconds;
        setTimeout(updateTimeRemaining, 1000);
    });
};

var updateTimeRemaining = function() {
    secondsRemaining -= 1;

    if (secondsRemaining <= 0) {
        // window.location = '/member/';
        $('#time_remaining_alert').removeClass('show');
        $('#timeout-modal').show().addClass('show');
        $('.modal-wrapper').css('z-index', '10000');
        return;
    }

    var minutes = parseInt(secondsRemaining / 60, 10),
        seconds = secondsRemaining % 60,
        format = '';

    if (secondsRemaining <= 180) {
        if (seconds < 10) {
            format = minutes + ':0' + seconds;
        } else {
            format = minutes + ':' + seconds;
        }

        $('#time_remaining').html(format);
        var $alert = $('#time_remaining_alert');
        if (!$alert.hasClass('show') && !$alert.hasClass('shown')) {
            $alert.addClass('show shown');
        }
    }

    setTimeout(updateTimeRemaining, 1000);
};


$('.x-grey-lg', '#timeout-modal').on(clickAction, function(e) {
    e.preventDefault();
    window.location = '/member/';
});

$('.row-overlay .x-grey-lg').on('click', function(e) {
    $(this).parents('.row-overlay').fadeOut();
});

$('.message-layer .x-grey-lg').on('click', function(e) {
    $(this).parents('.message-layer').fadeOut();
});

$('.waitlist').on(clickAction, function(e){
    e.preventDefault();

    url = $(this).attr('href');
    data = {};

    $.ajax({
        type: 'POST',
        url: url,
        data: data,
        success: function(data) {
            displayMessage(data);
        },
        error: function(data){
            var errorMessage = 'There was an error updating the waitlist. Please stand by.';
            displayMessage(errorMessage);
        }
    });
    return false;
});

$('#waitlist_link').click(function(e){
    e.preventDefault();

    url = $(this).attr('href');
    data = {};

    $.ajax({
        type: 'POST',
        url: url,
        async: true,
        data: data,
        dataType: 'html',
        success: function(data) {
            displayMessage(data);
            $('.mobile-actions').hide().removeClass('show');
        },
        error: function(data){
            var errorMessage = 'There was an error updating the waitlist. Please stand by.';
            displayMessage(errorMessage);
            $('.mobile-actions').hide().removeClass('show');
        }
    });
    return false;
});



$(function() {
    // start timer
    timeRemaining();

    // when the user changes the companion count, submit the form automatically
    $('#id_companion_count').change(function(){
        // remove all flights for visual effect
        $('.flight-table, #flight_buttons').remove();
        // submit the form
        $('#companion_count').submit();
    });

    $('#id_companions_only').change(function(){
        // remove all flights for visual effect
        $('.flight-table, #flight_buttons').remove();
        // submit the form
        $('#companion_count').submit();
    });


    // when the user changes the flight filter, update the flight results display
    $('#id_filters').change(function(){
        filter = $(this).val() ? $(this).val() : 'all-flights';
        filter_attr = 'data-' + filter;
        $('.flight-table').hide();
        $('.flight-table['+filter_attr+'="true"]').fadeIn();
    });

    // when the user changes the reservation filter, reload the flight reservation query
    $('#id_reservation_filters').change(function(){
        filter = $(this).val() ? $(this).val() : 'all-flights';
        baseUrl = '/flight/reservations/';
        switch (filter){
            case 'all-flights':
                window.location.href = baseUrl + 'all/';
                break;
            case 'upcoming-flights':
                window.location.href = baseUrl + 'upcoming/';
                break;
            case 'complete-flights':
                window.location.href = baseUrl + 'complete/';
                break;
            case 'alpha-last-name-flights':
                window.location.href = baseUrl + 'all/?sort=a-z';
                break;
            case 'reverse-alpha-last-name-flights':
                window.location.href = baseUrl + 'all/?sort=z-a';
                break;
            case 'promotional-flights':
                window.location.href = baseUrl + 'all/?type=promo';
                break;
            case 'fun-flights':
                window.location.href = baseUrl + 'all/?type=fun';
                break;
        }
    });

    // when the user changes the reservation filter, reload the flight reservation query
    $('#id_member_filters').change(function(){
        member = $(this).val() ? $(this).val() : 'all';
        filter_attr = '[data-member="'+member+'"]';
        $('.reservation-row.fadeIn').removeClass('fadeIn');
        $('.reservation-row').addClass('fadeOut');
        if (member == 'all'){
            $('.reservation-row').removeClass('fadeOut').addClass('fadeIn');
        }
        else{
            $('.reservation-row'+filter_attr).removeClass('fadeOut').addClass('fadeIn');
        }
    });

    //// Flight select
    $('.flight-table').on(clickAction, function() {
        var $this = $(this),
            flightId = $this.data('flight-id'),
            destinationCode = $this.data('destination');

        if ($this.hasClass('full') || $this.hasClass('unavailable')) {
            if ($this.hasClass('full')) {
                var waitlistUrl = $this.data('waitlist'),
                    similarUrl = $this.data('similar');

                $('#waitlist_link').attr('href', waitlistUrl);
                $('#similar_link').attr('href', similarUrl);

                $('.mobile-actions').show();
                setTimeout(function() {
                  $('.mobile-actions').addClass('show');
                });
            }
        } else {
            $this.siblings().removeClass('selected');
            $this.addClass('selected');

            $('#nav-destination').html(destinationCode);

            $('#flight_id').val(flightId);

            $('.disabled').removeClass('disabled').removeAttr('disabled');
        }
    });

    //// Companion select check behavior
    $('.companion-check input:checked').each(function() {
        $(this).parent().addClass('checked');
    });
    $('.companion-check').on(clickAction, function() {
        var checkbox = $('input[type=checkbox]', this);
        $(this).toggleClass('checked');
        if(checkbox.is(':checked')) {
            checkbox.prop('checked', false);
        } else {
            checkbox.prop('checked', true);
        }
    });


    // confirmation payment view

    $('#use_another_card').on(clickAction, function(event) {
        event.preventDefault();
        $('.selected').removeClass('selected');
        $(this).addClass('selected');
        $('#payment_information_form').show();
        $('.disabled').removeClass('disabled').removeAttr('disabled');
    });

    $('#use_this_card').on(clickAction, function(event) {
        event.preventDefault();
        $('.selected').removeClass('selected');
        $(this).addClass('selected');
        $('#payment_information_form').hide();
        $('#cc-number').val(''); // ensure form is cleared so it doesnt submit to stripe
        $('.disabled').removeClass('disabled').removeAttr('disabled');
    });

    $('#use_this_bank_account').on(clickAction, function(event) {
        event.preventDefault();
        $('.selected').removeClass('selected');
        $(this).addClass('selected');
        $('#payment_information_form').hide();
        $('#cc-number').val(''); // ensure form is cleared so it doesnt submit to stripe
        $('.disabled').removeClass('disabled').removeAttr('disabled');
    });


    $('#team_member_picker').on(clickAction, function() {
        $('#team_picker_modal').show().addClass('show');
    });

    $('.cancel-flight-reservation').on(clickAction, function(event) {
        // prevent the a link click from going through
        event.preventDefault();

        var $this = $(this),
            url = $this.attr('href'), // URL to send the AJAX request to
            id = $this.data('id'); // the class to target for removal

        $.get(url, function(data) {
            // if no reservations left and on confirm view, redirect to booking start
            if (data.flight_reservation_count === 0 && window.location.pathname === '/book/confirm/') {
                window.location = '/book/';
            }
            // remove the flight reservation rows from view
            $(id).remove();
            // update flight reservation counts
            $('.flight_reservation_count').html(data.flight_reservation_count);
            // udpate total pass values throughout the HTML
            $('.total_available_passes').html(data.total_available_passes);
            $('.total_available_companion_passes').html(data.total_available_companion_passes);
        });
    });

    $('.cancel-flight-button').on(clickAction, function(event) {
        event.preventDefault();

        // show confirmation dialog
        $('#cancel-modal').show().addClass('show');

    });

    $('.message-layer > .x-grey-lg').on(clickAction, function() {
        $(this).parent().fadeOut(500, 'linear', function(){
            //if ($(this).parent().hasClass('cancelled')){
            //   $(this).parent().addClass('dismissed');
            //}
        });
    });

    $('body').on(clickAction, 'a.upgrade', function(event) {
        event.preventDefault();

        var plan = $(this).data('plan');
        var url = '/profile/plan/upgrade/' + plan + '/';
        $('#confirm_upgrade').attr('href', url);
        $('#upgrade_modal').hide();
        $('#confirm_modal').show();
    });
});

function displayMessage(message){
    var $message;

    if (message.indexOf('<div') === 0) {
        $message = message;
    } else {
        $message = $('<div class="modal-wrapper" style="display: block; z-index: 10000; opacity: 1;"><div class="modal center"><figure class="x-grey-lg"></figure><figure class="alert-icon"></figure><p class="thick">'+message+'</p><a href="" class="dismiss action-block grey condensed">Okay, got it<figure class="arrow-right-grey"></figure></a></div></div>');
    }

    $('body').prepend($message);
    $('.x-grey-lg').on(clickAction, function(e) {
        e.preventDefault();
        location.reload();
    });
}
