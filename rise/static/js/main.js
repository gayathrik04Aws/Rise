$('a.big-circle-button').hover(function() {
  $('.slidey-label').toggleClass('slide');
});

$('.select-city input').on('change', function() {
    if($('#other-city').is(':checked')) {
        $('#write-in-city:not(:hidden)').removeAttr('disabled');
        $('#write-in-city').focus();
    } else {
        $('#write-in-city').val('').attr('disabled', 'disabled');
    }
});

$('.faq li').click(function() {
  if($('.answer', this).hasClass('expanded')) {
    $('.expand-state', this).html('+');
  } else {
    $('.expand-state', this).html('-');
  }
  $('.answer', this).slideToggle(300).toggleClass('expanded');
});

$(window).on('load resize', function() {
  if($(this).width() < 768) {
    $('.faq h3').addClass('mobile');
  } else {
    $('.faq h3').removeClass('mobile');
    $('.faq ul').show();
  }
});

$('.faq h3').click(function() {
  var questions = $('ul', $(this).parent());
  if($(this).hasClass('mobile')) {
    questions.slideToggle(300);
    $(this).toggleClass('expanded');
  }
});

$('.dismiss').click(function(){
    $(this).parent().slideUp();
});

function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

$('#learn-more-arrow').click(function(e) {
    e.preventDefault();
    var offset = $("#learn-more-target").offset();
    var body = $("html, body");
    body.animate({scrollTop:offset.top}, '700', 'swing', function() {

    });
});

$(".email-share .button").click(function(){
  $(this).addClass('sending');
});

setTimeout(function() {
  $(".email-share .button").removeClass("sending");
}, 3000);

// BEGIN VIMEO VIDEO  PLAYER
var iframe = $('#player1')[0];
if (iframe){
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
}

// END VIDEO PLAYER

function numberWithCommas(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function decimalAdjust(type, value, exp) {
    // If the exp is undefined or zero...
    if (typeof exp === 'undefined' || +exp === 0) {
      return Math[type](value);
    }
    value = +value;
    exp = +exp;
    // If the value is not a number or the exp is not an integer...
    if (isNaN(value) || !(typeof exp === 'number' && exp % 1 === 0)) {
      return NaN;
    }
    // Shift
    value = value.toString().split('e');
    value = Math[type](+(value[0] + 'e' + (value[1] ? (+value[1] - exp) : -exp)));
    // Shift back
    value = value.toString().split('e');
    return +(value[0] + 'e' + (value[1] ? (+value[1] + exp) : exp));
}

// Decimal round
if (!Math.round10) {
    Math.round10 = function(value, exp) {
      return decimalAdjust('round', value, exp);
    };
}

$(function() {
    $('#mc-embedded-subscribe-form').submit(function(event) {
        var $form = $(this);

        $('#mc-embedded-subscribe-form .error-message, #mc-embedded-subscribe-form .form-success').hide();

        $.ajax({
            type: $form.attr('method'),
            url: $form.attr('action'),
            data: $form.serialize(),
            cache: false,
            dataType: 'json',
            contentType: "application/json; charset=utf-8",
            error: function(err) {
                $('#mc-embedded-subscribe-form .error-message').show();
                },
            success: function(data) {
                if (data.result === 'success') {
                    $('#mc-embedded-subscribe-form .form-success').show();
                    $('#mc-embedded-subscribe-form input, #mc-embedded-subscribe-form button').hide();
                } else {
                    if(data.msg.toLowerCase().indexOf("is already subscribed") > -1) {
                        $('#mc-embedded-subscribe-form .error-message.already-subscribed').show();
                    } else {
                        $('#mc-embedded-subscribe-form .error-message.general-error').show();
                    }
                }
            }
        });

        return false;
    });

    ////
    //// Range Slider functionality
    var $document   = $(document),
        $inputRange = $('input[type="range"]');

    function valueOutput(element) {
        var value = element.val();
        var $output = $('output', $(element).parent()).first(),
            $range_slider = $('.rangeslider', $(element).parent()).first();
            $handle = $('.rangeslider__handle', $(element).parent()).first();
        $output.html(value);
        $output.css('left', ($handle.position().left - 0)+'px');
    }

    $inputRange.on('change', function(e){
        valueOutput($(this));
    });
    $inputRange.each(function(){
        $curr_element = $(this);
        $(this).rangeslider({
            polyfill:false,
            onInit: function() {
                valueOutput($curr_element);
            },
            onSlide: function(position, value) {
                valueOutput($curr_element);
                updateCalculator();
            },
            onSlideEnd: function(position, value) {}
        });
    });
    // end Range Slider
});

////
//// DETECT IF THE USER IS MOBILE
var isMobile = {
  Android: function() { return navigator.userAgent.match(/Android/i); },
  BlackBerry: function() { return navigator.userAgent.match(/BlackBerry/i); },
  iOS: function() { return navigator.userAgent.match(/iPhone|iPad|iPod/i); },
  Opera: function() { return navigator.userAgent.match(/Opera Mini/i); },
  Windows: function() { return navigator.userAgent.match(/IEMobile/i); },
  any: function() { return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Opera() || isMobile.Windows()); } };



////
//// Define 'tap' event
(function () {
  var touchStart = {};
  var touchEnd = {};

  $('body').on('touchstart', function(e) {
    touchStart.x = e.originalEvent.changedTouches[0].screenX;
    touchStart.y = e.originalEvent.changedTouches[0].screenY;
  });
  $('body').on('touchend', function(e) {
    touchEnd.x = e.originalEvent.changedTouches[0].screenX;
    touchEnd.y = e.originalEvent.changedTouches[0].screenY;
    if(Math.abs(touchStart.x - touchEnd.x) < 10 && Math.abs(touchStart.y - touchEnd.y) < 10) { // Threshold can be set here.
      $(e.target).trigger('tap');
    }
  });
})();



////
//// On Dekstop, click events will be 'click', on Mobile, 'tap'
var clickAction = (isMobile.any()) ? 'tap' : 'click';



$('*').on(clickAction, function(e) {
  //console.log(e.target);
});



////
//// Handle various custom selects
$('.select').not('.fullscreen').on(clickAction, function(e) {
  e.stopPropagation();
  var options = $('ul', this),
      option = $('li', this),
      nativeSelect = $('select', this),
      value = $('.value', this);

  $(this).toggleClass('expand');
  options.toggleClass('expand');

  option.on(clickAction, function() {
    var optionValue = $(this).attr('value');

    value.html($(this).html());
    nativeSelect.attr('value', optionValue);
    nativeSelect.val(optionValue);
    nativeSelect.change();
  });
});

$('.select').each(function() {
    var nativeSelect = $('select', this),
    value = $('.value', this);

    if (nativeSelect) {
        var text = $('option[value="' + nativeSelect.val() + '"]', this).text();
        value.text(text);
    }
});

var city_bgs = {
  'austin': 'img/background_images/desktop/'
};

function updateSelectBG() {
  $('.select.fullscreen').each(function() {
    var $this = $(this),
        currentValue = $('.value', this).html().toLowerCase(),
        classes = $this.parent('.block').attr('class').split(' '),
        bgClass = $.grep(classes, function(c, i) {
            return c.match(/^background\-/);
        })[0];

    $(this).parent('.block').removeClass(bgClass).addClass('background-'+currentValue);
    // if(isMobile.any()) {
    //   $(this).parent('.block').removeClass(css('background-image', 'url(../img/background_images/mobile/'+currentValue+'-mobile.jpg)');
    // } else {
    //   $(this).parent('.block').css('background-image', 'url(../img/background_images/desktop/image-bg-'+currentValue+'.jpg)');
    // }
  });
}

$('.select.fullscreen').on(clickAction, function() {
  var $this = $(this),
      currentValue = $('.value', this),
      allButOptions = $this.parent('.fullscreen').find('*').not('.select, ul, ul li, select'),
      options = $('ul', this),
      option = $('li', this),
      submitButton = $('.receive-data', $(this).parent('.fullscreen')),
      nativeSelect = $('select', this);
      alignContainer = $('.block.pattern.fullscreen');

  allButOptions.addClass('hide');
  $this.addClass('hide-icon');
  setTimeout(function() {
    options.addClass('expand');
    alignContainer.addClass('align-fullscreen');
    setTimeout(function(){
      alignContainer.css('display', 'block');
    }, 300);
  }, 300);

  option.on(clickAction, function(e) {
    e.stopPropagation();
    var optionValue = $(this).attr('value');

    submitButton.attr('href', optionValue);
    $(this).siblings().removeClass('active');
    $(this).addClass('active');
    nativeSelect.val(optionValue);
    nativeSelect.attr('value', optionValue);
    currentValue.html($(this).html());
    setTimeout(function() {
      options.removeClass('expand');
      alignContainer.removeClass('align-fullscreen');

      updateSelectBG();
      setTimeout(function() {
        allButOptions.removeClass('hide');
        alignContainer.css('display', 'table-cell');
        $this.removeClass('hide-icon');
      }, 500);
    }, 500);
  })
});




////
//// Dropdown Alerts and Modals
$('.dropdown-alert .action-block').on(clickAction, function() {
  $('.dropdown-alert').removeClass('show');
});

$('.modal .dismiss, .modal .x-grey-lg').not('#timeout-modal .x-grey-lg').on(clickAction, function() {
  $('.modal-wrapper').removeClass('show').hide();
});


////
//// A Better expandable div with unknown height
$('.toggle-expandable').on(clickAction, function() {
  var nearestExpandable = $(this).parentsUntil('.expand-wrap').siblings('.expandable-height'),
      heights = 0;

  if(!$(this).hasClass('popover-button')) {
    $(this).toggleClass('active');
  }

  if(nearestExpandable.hasClass('expanded')) {
    nearestExpandable.css('height', 0).removeClass('expanded');
  } else {
    nearestExpandable.children().each(function() { heights += $(this).outerHeight(true) });
    nearestExpandable.css('height', heights).addClass('expanded');
  }
});

// ////
// //// Popover behavior
// $('.popover-button').on(clickAction, function() {
//   var thisPopover = $(this).children('.popover');

//   $('.popover-button').not($(this)).removeClass('active');
//   $('.popover.show').not(thisPopover).removeClass('show');
//   thisPopover.toggleClass('show');
//   $(this).toggleClass('active');
// });

$('.popover-control').on(clickAction, function(e) {
  var nextPopover = $(this).siblings('.popover');
  var parent = $(this).parent('.popover-button');

  e.stopPropagation();

  nextPopover.toggleClass('show');
  parent.toggleClass('active');
});
$('figure.popover-button').on(clickAction, function(e) {
  var $popover = $('.popover', $(this));

  e.stopPropagation();

  $('.popover-button').not($(this)).removeClass('active');
  $('.popover.show').not($popover).removeClass('show');
  $popover.toggleClass('show');
  $(this).toggleClass('active');
});


$('.flight-table .actions .popover li, .dashboard .location .popover li').on(clickAction, function(e) {
  e.stopPropagation();
  $('.flight-table .actions .popover li, .dashboard .location .popover li').not($(this)).removeClass('active');
  $(this).addClass('active');
});


////
//// Profile Nav auto hide
$(function(){
  if ($('body').hasClass('dashboard')) {
      $(window).on('scroll', function() {
        var scrollTop = $(window).scrollTop();
        if(scrollTop > 80) {
          $('nav.profile').addClass('show');
        } else {
          $('nav.profile').removeClass('show');
          if($('.mobile-nav-dropdown').hasClass('expanded')) {
            $('.mobile-nav-dropdown').attr('style', '');
            $('nav.profile .toggle-expandable').removeClass('active');
          }
        }
      });
   } else {
    $('nav.profile').addClass('show');
  }
});


////@TODO May need something like this if absolutely positioned nav is no good.
//// Fade color of translucent nav on scroll
/*$(function(){
    if ($('nav').hasClass('light')) {
        var rgba = $('nav').css('background-color').replace(/^rgba\((.*)\)$/, '$1').split(', '),
            alpha = Number(rgba[3]);
        $(window).on('scroll', function() {
            var scrollTop = $(window).scrollTop();
                $('nav').css('background-color', 'rgba('+rgba[0]+', '+rgba[1]+', '+rgba[2]+', '+(alpha + (scrollTop * 0.0108))+')')
        });
    }
});*/



////
//// 'Let's Fly Dropdown'
$('.lets-fly-button').on(clickAction, function() {
  $('.lets-fly-dropdown').toggleClass('show');
});

$('.lets-fly-dropdown li').on(clickAction, function(e) {
  e.stopPropagation();
  $(this).siblings().removeClass('active');
  $(this).addClass('active');
});


////
//// Chart key modal
$('.toggle-chart-key').on(clickAction, function() {
  $('.mobile-chart-key').show();
  setTimeout(function() {
    $('.mobile-chart-key').addClass('show');
  });
});

$('.action-block', '.mobile-chart-key, .mobile-actions').on(clickAction, function() {
  $('.mobile-chart-key, .mobile-actions').removeClass('show');
  setTimeout(function() {
    $('.mobile-chart-key, .mobile-actions').hide();
  }, 400);
});

////
//// Reveal checkboxes
$('.reveal-checkbox').change(function(){
  var parentReveal = $(this).closest('.revealable');
  var nearestExtraInputs = $(this).parentsUntil('.revealable').siblings('.revealable-block');

  if ($(this).is(':checked')) {
    parentReveal.addClass('revealed-checkbox');
    nearestExtraInputs.toggle();
  } else {
    parentReveal.removeClass('revealed-checkbox');
    nearestExtraInputs.toggle();
  }
});

////
//// Beginning input
$('.membership-type-checkbox').change(function(){
  var nearestBeginningInput = $(this).parentsUntil('.check-radio-block').siblings('.beginning-input');
  if ($(this).is(':checked')) {
    nearestBeginningInput.toggle();
  } else {
    nearestBeginningInput.toggle();
  }
});

////
//// Filters
// $(function(){
//   $('div.filters').selectable();
// });

////
//// Break underline around descenders
$('a.underline-link').each(function () {
    var u = '<span class="underline">',
        decoded;
    $(this).prop('innerHTML', function (_, html) {
        u += html.replace(/&amp;/g, '&').replace(/(g|j|p|q|y|Q|@|{|_|\(|\)|\[|\||\]|}|;|,|§|µ|ç|\/)/g, '</span>$1<span class="underline">');
        u += '</span>';
        $(this).html(u);
    });
});

////
//// Clickable TR
$('.link-row').on(clickAction, function(){
  window.document.location = $(this).attr("href");
});

////
//// Print page
$('#print-page').on(clickAction, function(){
    window.print();
});

////
//// Link to FAQ membership-anchor
$(function() {
    if ( document.location.href.indexOf('#faq-membership-level') > -1 ) {
        $('li.membership-level-dropdown').click();
    }
});

$('#learn_more_button').on(clickAction, function(event) {
    event.preventDefault();
    $('#learn_more_modal').show();
});

$('#id_member_count, #id_pass_count').change(function() {
    updateCorporateSignupAmounts();
});

$(function() {
    updateCorporateSignupAmounts();
});

// FORMATTING
$('#id_phone, #id_mobile_phone, #phone-number').formatter({
// $('#id_phone, #id_mobile_phone, #phone-number, .referral-phone').formatter({
    'pattern': '{{999}}-{{999}}-{{9999}}',
    'persistent': false
});

$('#id_date_of_birth, #id_start_date, .date-formatter').formatter({
    'pattern': '{{99}}/{{99}}/{{9999}}',
    'persistent': false
});

$('#id_duration, #id_takeoff_time, .time-formatter').formatter({
    'pattern': '{{99}}:{{99}}',
    'persistent': false
});

$('#id_verify_1, #id_verify_2').formatter({
    'pattern': '{{9}}.{{99}}',
    'persistent': false
});

////
//// Functions for displaying calculated corporate cost amounts
function updateCalculator(){
    var depositCost = 750;

    $calculator = $('#calculator-results');
    $numMembers = $('#num-members');
    $numSeats = $('#num-seats');
    if ($calculator && $numMembers && $numSeats){
        calculatedValue = corporateCost(parseInt($numMembers.val()), parseInt($numSeats.val()));
        $('span', $calculator).html(numberWithCommas(calculatedValue));
        deposit = parseInt($numMembers.val()) * depositCost;

        $('span.deposit-amount', '#calculator-deposit').html(numberWithCommas(deposit));
    }
}

function updateCorporateSignupAmounts() {
    var depositCost = 750,
        members = parseInt($('#id_member_count').val()),
        passes = parseInt($('#id_pass_count').val()),
        total = corporateCost(members, passes),
        deposit = members * depositCost,
        depositTax = Math.round10((deposit * .0825), -2).toFixed(2),  // FET tax rounded to the nearest cent
        $total = $('#monthly_total'),
        $deposit = $('#deposit');

    $total.html('$' + numberWithCommas(total));
    $deposit.html('$' + numberWithCommas(deposit));
}

////
//// Formula for corporate cost
function corporateCost(members, passes){
    var baseCost = 3700,
        saveMySeatCost = 925,
        passThreshold = 4;

    var total = baseCost + (passes - passThreshold) * saveMySeatCost;

    return total;
}
