function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// BEGIN VIMEO VIDEO  PLAYER
var iframe = $('#player1')[0];
var player = $f(iframe);
var windowWidth = $(window).width();
var width = 853;
var height = 480;


if (windowWidth < width) {
    width = 640;
    height = 360;
}

if (windowWidth < width) {
    width = 560;
    height = 315;
}

if (windowWidth < width) {
    width = windowWidth - 10;
    height = 315 / 560 * width;
}

$('#player1').css({
  'width': width,
  'height': height
});

player.addEvent('ready', function() {
    player.addEvent('finish', onFinish);
});

$('.play-button').click(function() {
    $('.video-modal').fadeIn(500, function() {
        if (! isMobile()) {
            player.api('play');
        }
    }).css('display', 'table');
    $('.video-modal').click(function() {
        $(this).fadeOut(500);
          player.api('pause');
    });
});

function onFinish(id) {
  $('.video-modal').fadeOut(500);
}

// END VIDEO PLAYER
