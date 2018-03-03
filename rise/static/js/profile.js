// Filter reservations
$('#flight-sort-filter input[type="radio"]').click(function(e){
    button_id = $(this).attr('id');
    if (button_id === 'all'){
        $('#flight-results li').show();
    }
    else if (button_id === 'past'){
        $('#flight-results li.status-upcoming').hide();
        $('#flight-results li.status-past').show();
    }
    else if (button_id === 'upcoming'){
        $('#flight-results li.status-past').hide();
        $('#flight-results li.status-upcoming').show();
    }
    else if (button_id === 'promotional'){
        $('#flight-results li.type-r, #flight-results li.type-f').hide();
        $('#flight-results li.type-p').show();
    }
    else if (button_id === 'fun'){
        $('#flight-results li.type-r, #flight-results li.type-p').hide();
        $('#flight-results li.type-f').show();
    }
});

// Cancel Flight Reservation
$('#flight-results .cancel-flight').click(function(e){
    e.preventDefault();
    url = $(this).attr('href');
    flight = $(this).attr('data-flight');
    $.ajax({
        type: 'GET',
        url: url,
        dataType: 'json',
        success: function(data) {
            if ('success' in data){
                var successMessage = 'Your reservation for Flight ' + flight + ' has been cancelled successfully. Thanks!';
                displayMessage(successMessage);
            }
            else if ('error' in data){
                displayMessage('Error: ' + data['error']);
            }
        },
        error: function(data){
            var errorMessage = 'There was an error canceling your reservation for Flight ' + flight + '.';
            displayMessage(errorMessage);
        }
    });

});

// Reschedule Flight Reservation
$('#flight-results .reschedule-flight').click(function(e){
    e.preventDefault();
    var confirmation = confirm("Rescheduling will cancel your flight reservation on this flight.");
    if (confirmation == true){
        window.location = $(this).attr('href');
    }
});
$(function() {
    $('#change-avatar').click(function(event) {
        event.preventDefault();
        $('#avatar-file-input').click();
    });
    $('#change-avatar-mobile').click(function(event) {
        event.preventDefault();
        $('#avatar-file-input-mobile').click();
    });
    $('#change-avatar-tablet').click(function(event) {
        event.preventDefault();
        $('#avatar-file-input-tablet').click();
    });
    // TODO: change navbar image also
    $('#avatar-file-input,#avatar-file-input-tablet,#avatar-file-input-mobile').change(function() {
        var $this = $(this),
            files = this.files;

        if (files.length > 0) {
            var file = files[0];

            /* post avatar */
            var url = $('#update-avatar').attr('action');
            var formData = new FormData();
            formData.append('avatar', file);
            //var formData = new FormData($('#update-avatar')[0]);
            postAvatar(url, formData);

            /* display new avatar on page */
            var previewUrl = window.URL.createObjectURL(file);
            var bin = new FileReader();
            bin.readAsBinaryString(file);
            bin.onloadend = function(e) {
                bin_file = new BinaryFile(e.target.result);
                var file_exif = EXIF.readFromBinaryFile(bin_file);
                file_orientation = file_exif.Orientation;
                if (file_orientation == '3'){
                    $('#avatar-image').css('transform','rotate(180deg)');
                }
                else if (file_orientation == '6'){
                    $('#avatar-image').css('transform','rotate(90deg)');
                }
                else if (file_orientation == '8'){
                    $('#avatar-image').css('transform','rotate(270deg)');
                }
                $('#avatar-image').css('background-image', 'url(' + previewUrl + ')');
            }
        }
    });

    $('#request-more-invites').on('submit', function(e){
        e.preventDefault();
        var url = $(this).attr('action');
        var data = {
            'first_name': $('#request-first-name').val(),
            'last_name': $('#request-last-name').val(),
            'email': $('#request-email').val()
        };
        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            success: function(data) {
                if ('success' in data){
                    var successMessage = 'Your request has been sent. Thanks!';
                    displayMessage(successMessage);
                }
                else if ('error' in data){
                    displayMessage('Error: ' + data['error']);
                }
            },
            error: function(data){
                var errorMessage = 'There was an error requesting an invite. Please stand by.';
                displayMessage(errorMessage);
            }
        });
    });
});

$('.home-location li').on(clickAction, function(){
    var $new_origin = $(this);
    if (!$new_origin.hasClass('active')){
        var $parent = $(this).parent()
        var data = {
            'origin_pk': $new_origin.attr('data-origin_pk')
        }
        var url = $parent.attr('data-action');
        var origin_name = $new_origin.text();

        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            success: function(data) {
                if ('success' in data){
                    var successMessage = 'Your hometown has been changed.';
                    displayMessage(successMessage);
                    $('#user-origin').html(origin_name);
                    $('.active', $parent).removeClass('active');
                    $new_origin.addClass('active');
                }
                else if ('error' in data){
                    displayMessage('Error: ' + data['error']);
                }
            },
            error: function(data){
                var errorMessage = 'There was an error updating your hometown. Please stand by.';
                displayMessage(errorMessage);
            }
        });
    }

});
function addUpdateMember(showChargeMsg){
    var frm = $("#addUpdateMemberForm");
    if(showChargeMsg=='True'){
        var showBox = false;
        var checked = $(frm).find('[id^=member-group]:checked');
        for(var i=0;i<checked.length;i++){
            var lbl = $.trim(checked[i].labels[0].innerText);

            if(lbl != "Coordinator"){
                showBox=true;
                break;
            }
        }
        if(showBox){
             $("#memberChargeModal").show();
        }else{
            frm.submit();
        }
        return false;
    }else{
        frm.submit();
    }
}

function submitAddUpdateMemberForm(){
     $("#addUpdateMemberForm").submit();
}

$('.permission-change').change(function(){
    var form = this.form;
    url = $(form).attr('action');
    data = $(form).serialize()

    $.ajax({
        type: 'POST',
        url: url,
        data: data,
        dataType: 'json',
        success: function(data) {
            if ('success' in data){
                var successMessage = 'The permissions have been updated for the member.';
                displayMessage(successMessage);
            }
            else if ('error' in data){
                displayMessage('Error: ' + data['error']);
            }
        },
        error: function(data){
            var errorMessage = 'There was an error updating the member\'s permissions. Please stand by.';
            displayMessage(errorMessage);
        }
    });
});
$('.cancel-account').on(clickAction, function(){
    var errorMessage = 'Contact Rise Support at 844 359 7473 or <a href="mailto:members@iflyrise.com">members@iflyrise.com</a> to make a change to your plan.';
    displayMessage(errorMessage);
})

function postAvatar(url, data){
    $.ajax({
        type: "POST",
        url: url,
        data: data,
        cache: false,
        processData: false,
        contentType: false,
        success: function(data){
            var successMessage = 'Your picture has been changed!';
            displayMessage(successMessage);
        },
        error: function(data){
            var errorMessage = 'There was an error updating your avatar.';
            displayMessage(errorMessage);
        },
        dataType: 'json'
    });
}

function displayMessage(message){
    var $message = $('<div class="modal-wrapper" style="display: block; z-index: 10000; opacity: 1;"><div class="modal center"><figure class="x-grey-lg"></figure><figure class="alert-icon"></figure><p class="thick">'+message+'</p><a href="" class="dismiss action-block grey condensed">Okay, got it<figure class="arrow-right-grey"></figure></a></div></div>');
    $('body').prepend($message);
    $('.x-grey-lg').on(clickAction, function(e) {
        e.preventDefault();
        location.reload();
    });
}

////
//// Start showcase
$(document).ready(function(){
    if($(window).width() < 768 ) {
        $('#showcase').awShowcase({
            content_height: 120,
            content_width: "auto",
            auto: true,
            interval: 5000,
            continuous: true
        });
    } else {
       $('#showcase').awShowcase({
            content_height: 70,
            content_width: "auto",
            auto: true,
            interval: 5000,
            continuous: true
        });
    }
});
