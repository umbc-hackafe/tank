$(function() {
    window.client = new Client(location.host, location.port, "/ws", function() {
	setInterval(function() {
	    window.client.call("ping");
	}, 500);
    });

    $("#passcode").focus();

    $("#passcode").keyup(function(evt) {
	if ($("#passcode").val().slice(-1) == '#') {
	    $("#passcode").val($("#passcode").val().slice(0,-1));
	    $("#auth-form").submit();
	}
    });

    $("#auth-form").submit(function(){auth(); return false;});


    $("#background-text").append(document.createTextNode($(document.body).html()));
    setTimeout(function(){runText();}, 40);

    $("#speech-button").click(function(){speak($("#speech").val(), function(){$("#speech").val('');})});
    $("#control-form").submit(function(){speak($("#speech").val(), function(){$("#speech").val('');})});

    $("#self-destruct").click(function() {
	speak("Self-destruct sequence initiated.", function(){countdown(30, function(){speak("Self-destruct canceled")});});
    });

    $(document).keydown(function(e) {
	switch(e.which) {
	case 37: // left
	case 38: // up
	case 39: // right
	case 40: // down
	    return;

	case 87: // W
	case 65: // A
	case 83: // S
	case 68: // D
	    return;

	case 48: // 0
	case 49: // 1
	case 50: // 2
	case 51: // 3
	case 52: // 4
	case 53: // 5
	case 54: // 6
	case 55: // 7
	case 56: // 8
	case 57: // 9
	    return;

	case 70: // F (button down)
	    $("#turret-fire").click();
	    break;

	case 78: // N (button up)
	    sound("beep2");
	    break;

	case 76: // L (keyswitch ON)
	    sound("welcome");
	    break;

	case 85: // U (keyswitch OFF)
	    sound("shutdown");
	    break;
	}

	//e.preventDefault();
    });
	    
});

function countdown(time, cb) {
    speak(time);

    if (time > 0) {
	setTimeout(function() {countdown(time-1, cb);}, 1000);
    } else {
	cb();
    }
}

function sound(name) {
    $.get("/sound", {name: name});
}

function speak(text, cb) {
    $.get("/speak", {"text": text}, cb);
}

function auth() {
    if ($("#passcode").val() == "1337") {
	$("#auth-box").addClass('hidden');
	$("#access-granted-box").removeClass('hidden');

	speak("Access, Granted");

	setTimeout(function() {
	    $("#access-granted-box").addClass('hidden');
	    $("#control-box").removeClass('hidden');
	}, 3000);
    } else {
	$("#auth-box").addClass('hidden');
	$("#access-denied-box").removeClass('hidden');
	$(document.body).addClass("redalert");

	speak("Access, Denied");

	blink($("#denied-text"), 500, 6);

	setTimeout(function() {
	    $(document.body).removeClass("redalert");
	    $("#access-denied-box").addClass('hidden');
	    $("#auth-box").removeClass('hidden');
	}, 3000);
    }
}

function blink(element, delay, times) {
    if (times % 2) {
	$(element).addClass("dark");
	$(element).removeClass("light");
    } else {
	$(element).addClass("light");
	$(element).removeClass("dark");
    }

    if (times > 0) {
	setTimeout(function() {blink(element, delay, times-1);}, delay);
    }
}

function runText() {
    var elm = $("#background-text")[0];
    if (elm.scrollTop + elm.offsetHeight >= elm.scrollHeight) {
	elm.scrollTop = 0;
    } else {
	elm.scrollTop += 40;
    }
    setTimeout(function() {runText();}, 40);
}
