$(window).on('resize', function() {
  $('.carousel-wrap').each(function() {
    var $this = $(this),
        carousel = $('.carousel', $this)
        carouselSlideWidth = $this.width(),
        carouselSlides = carousel.children().length,
        activeSlide = 0,
        nav = $this.next(),
        navCircle = nav.find('li');
    carousel.children().css('width', carouselSlideWidth);
    carousel.css('width', carouselSlideWidth * carouselSlides);
  });
});


$('.carousel-wrap').each(function() {
  var $this = $(this),
      carousel = $('.carousel', $this)
      carouselSlideWidth = $this.width(),
      carouselSlides = carousel.children().length,
      activeSlide = 0,
      nav = $this.next(),
      navCircle = nav.find('li');
  carousel.children().css('width', carouselSlideWidth);
  carousel.css('width', carouselSlideWidth * carouselSlides);
  $('.left', nav).click(function() {
    if(activeSlide == 0) {
      carousel.css('left', -1* carouselSlideWidth * (carouselSlides - 1));
      $($(navCircle[activeSlide])).toggleClass('active');
      activeSlide = carouselSlides - 1;
      $($(navCircle[activeSlide])).toggleClass('active');
    } else {
      $($(navCircle[activeSlide])).toggleClass('active');
      activeSlide -= 1;
      $($(navCircle[activeSlide])).toggleClass('active');
      carousel.css('left', activeSlide * carouselSlideWidth * -1);
    }
  });
  $('.right', nav).click(function() {
    if(activeSlide == carouselSlides - 1) {
      carousel.css('left', 0);
      $($(navCircle[activeSlide])).toggleClass('active');
      activeSlide = 0;
      $(navCircle[activeSlide]).toggleClass('active');
    } else {
      $(navCircle[activeSlide]).toggleClass('active');
      activeSlide += 1;
      $(navCircle[activeSlide]).toggleClass('active');
      carousel.css('left', activeSlide * carouselSlideWidth * -1);
    }
  });
  $(navCircle).click(function() {
    carousel.css('left', $(this).index() * carouselSlideWidth * -1);
    $(navCircle[activeSlide]).toggleClass('active');
    activeSlide = $(this).index();
    $(navCircle[activeSlide]).toggleClass('active');
  });
});
