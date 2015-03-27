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

    $("#speech-button").click(speak);
    $("#control-form").submit(function(){speak(); return false;});
});

function speak() {
    $.get("/speak", {"text": $("#speech").val()}, function() {
	$("#speech").val('');
    });
}

function auth() {
    if ($("#passcode").val() == "1337") {
	$("#auth-box").addClass('hidden');
	$("#access-granted-box").removeClass('hidden');

	setTimeout(function() {
	    $("#access-granted-box").addClass('hidden');
	    $("#control-box").removeClass('hidden');
	}, 3000);
    } else {
	$("#auth-box").addClass('hidden');
	$("#access-denied-box").removeClass('hidden');
	$(document.body).addClass("redalert");

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
