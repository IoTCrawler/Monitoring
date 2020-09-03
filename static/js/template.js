let headerHeight = $('head').outerHeight();

$(window).bind('scroll', function () {
    if ($(window).scrollTop() > headerHeight) {
        $('#navbar').removeClass('navbar-top');
        $('#navbar').addClass('navbar-fixed-top');
    } else {
        $('#navbar').removeClass('navbar-fixed-top');
        $('#navbar').addClass('navbar-top');
    }
});
