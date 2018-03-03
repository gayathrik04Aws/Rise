////
//// Press slider
$('.slider').leanSlider({
    directionNav: '#slider-direction-nav',
    controlNav: '#slider-control-nav',
    directionNavPrevBuilder: function(prevText){
        return '<div class="back-arrow arrow">';
    },
    directionNavNextBuilder: function(nextText){
        return '<div class="next-arrow arrow">';
    },
    controlNavBuilder: function(index, slide){
        return '<a href="#" class="lean-slider-control-nav nav-key">•</a>';
    }
});
