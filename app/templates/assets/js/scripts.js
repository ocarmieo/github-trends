
jQuery(document).ready(function() { 
    
    /*
        Background slideshow
    */
    $('.top-content').backstretch([
                         "assets/img/backgrounds/1.jpg"
                       , "assets/img/backgrounds/2.jpg"
                       , "assets/img/backgrounds/3.jpg"
                      ], {duration: 3000, fade: 750});
    
    $('#top-navbar-1').on('shown.bs.collapse', function(){
        $('.top-content').backstretch("resize");
    });
    $('#top-navbar-1').on('hidden.bs.collapse', function(){
        $('.top-content').backstretch("resize");
    });
    
    /*
        Wow
    */
    new WOW().init();
    
    /*
        Countdown initializer
    */
    var now = new Date();
    var countTo = 25 * 24 * 60 * 60 * 1000 + now.valueOf();    
    $('.timer').countdown(countTo, function(event) {
        $(this).find('.days').text(event.offset.totalDays);
        $(this).find('.hours').text(event.offset.hours);
        $(this).find('.minutes').text(event.offset.minutes);
        $(this).find('.seconds').text(event.offset.seconds);
    });
        

});


jQuery(window).load(function() {
    /*
        Loader
    */
    $(".loader-img").fadeOut();
    $(".loader").delay(1000).fadeOut("slow");
});
