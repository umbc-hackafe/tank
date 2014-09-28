var src = "/frame.jpg";

function refreshImage() {
    var screwTheCache = Math.floor(Math.random() * 100000);
    $('#webcam').attr('src', src + "?" + screwTheCache);
    setTimeout(refreshImage, 1000);
}

$(document).ready(refreshImage);
