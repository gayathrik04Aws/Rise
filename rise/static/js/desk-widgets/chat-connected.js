$(function() {
    $('a[href*="endsession"]').on('click', function() {
        $('.chat-widget--connected__overlay').addClass('show');
        $('.chat-widget--connected__session__end').remove();
        $('.chat-widget--connected__session__timer').css('border-right', 'none');
    });
});
