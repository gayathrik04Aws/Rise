
$('.more-info').click(function(){
    $(this).children(".text").toggleClass("show");
    $(this).toggleClass("active");
});

$('.text.show').click(function(){
    $(this).removeClass("show");
    $(this).parent(".more-info").removeClass("active");
});
