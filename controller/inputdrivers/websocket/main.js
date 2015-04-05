$(function() {
    window.client = new Client("angel", 80, "/ws", function() {
	window.client.socket.addOnClose(function() {
	    $("#control-box").addClass("hidden");
	    $("#connection-lost-box").removeClass("hidden");
	});

	window.client.socket.addOnOpen(function() {
	    if ($("#auth-box").hasClass("hidden")) {
		$("#control-box").removeClass("hidden");
		$("#connection-lost-box").addClass("hidden");
	    }
	});

	setInterval(function() {
	    window.client.call("ping");
	}, 750);
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
	speak("Self-destruct sequence initiated.", function(){countdown(30, 1, function(){speak("Self-destruct aborted.")});});
    });

    $(document).keydown(function(e) {
	switch(e.which) {
	case 37: // left
	case 65: // A
	    window.left = true;
	    drive();
	    break;

	case 38: // up
	case 87: // W
	    window.forward = true;
	    drive();
	    break;

	case 39: // right
	case 68: // D
	    window.right = true;
	    drive();
	    break;

	case 40: // down
	case 83: // S
	    window.back = true;
	    drive();
	    return;

	case 81: // Q
	    window.turretLeft = true;
	    turret();
	    return;

	case 69: // E
	    window.turretRight = true;
	    turret();
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

    $(document).keyup(function(e) {
	switch(e.which) {
	case 37: // left
	case 65: // A
	    window.left = false;
	    drive();
	    break;

	case 38: // up
	case 87: // W
	    window.forward = false;
	    drive();
	    break;

	case 39: // right
	case 68: // D
	    window.right = false;
	    drive();
	    break;

	case 40: // down
	case 83: // S
	    window.back = false;
	    drive();
	    return;

	case 81: // Q
	    window.turretLeft = false;
	    turret();
	    return;

	case 69: // E
	    window.turretRight = false;
	    turret();
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

	/*case 70: // F (button down)
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
	}*/

	    //e.preventDefault();
	}
    });

    $(document).click(function() {
	sound("select7");
    });
});

function turret() {
    var speed;
    if (window.turretLeft) {
	speed = 1;
    } else if (window.turretRight) {
	speed = -1;
    } else {
	speed = 0;
    }

    window.client.call("spin", {"args": [speed]});
}

function drive() {
    var speed, steer;
    if (window.forward) {
	speed = 1;
    } else if (window.back) {
	speed = -1;
    } else {
	speed = 0;
    }

    if (window.left) {
	steer = -1;
    } else if (window.right) {
	steer = 1;
    } else {
	steer = 0;
    }

    window.client.call("drive", {"args": [speed, steer]});
}

function countdown(time, min, cb) {
    speak(time);

    if (time > min) {
	setTimeout(function() {countdown(time-1, min, cb);}, 1000);
    } else {
	setTimeout(cb, 1000);
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
	    $(document.body).css('background-image', 'url(http://angel:8080/?action=stream)');
	    $(document.body).css('text-align', 'right');
	    $(".container").css('text-align', 'right');
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
