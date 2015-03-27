function SocketWrapper(socket) {
    this.socket = socket;
    this.queuedData = [];
    this.onOpens = [];
    this.onMessages = [];
    this.onErrors = [];
    this.onCloses = [];
    this.open = false;
    this.closed = false;
    this.wrap(socket);
}

SocketWrapper.prototype.wrap = function(socket) {
    var that = this;
    socket.onmessage = function(evt) {that.__doOnMessage(evt);};
    socket.onerror = function(evt) {that.__doOnError(evt);};
    socket.onclose = function(evt) {that.__doOnClose(evt);};
    socket.onopen = function(evt) {that.__doOnOpen(evt);};
}

SocketWrapper.prototype.__doOnOpen = function(evt) {
    // Log the socket opening.
    console.log("WebSocket opened!")

    this.open = true;
    this.closed = false;
    // APPARENTLY, this is now socket.this
    for (var l in this.onOpens.slice(0)) {
	this.onOpens[l](evt);
    }

    for (var d in this.queuedData) {
	this.send(this.queuedData[d]);
    }
    this.queuedData = [];
}

SocketWrapper.prototype.__doOnMessage = function(evt) {
    var jsonData = JSON.parse(evt.data);
    //console.log("Receiving: ", jsonData);
    if (jsonData == null) {
	console.log("Data is null... that's weird.");
    } else {
	for (var l in this.onMessages.slice(0)) {
	    // Might need to do atob() here?
	    this.onMessages[l](jsonData);
	}
    }
}

SocketWrapper.prototype.__doOnError = function(evt) {
    for (var l in this.onErrors.slice(0)) {
	this.onErrors[l](evt);
    }
}

SocketWrapper.prototype.__doOnClose = function(evt) {
    // Log the closing
    console.log("WebSocket closed!");

    this.open = false;
    this.closed = true;

    for (var l in this.onCloses.slice(0)) {
	this.onCloses[l](evt);
    }
}

SocketWrapper.prototype.addOnOpen = function(cb) {
    if (this.open) {
        cb();
    }
    this.onOpens.push(cb);
}

SocketWrapper.prototype.addOnMessage = function(cb) {
    this.onMessages.push(cb);
}

SocketWrapper.prototype.addOnError = function(cb) {
    this.onErrors.push(cb);
}

SocketWrapper.prototype.addOnClose = function(cb) {
    if (!this.open) {
        cb();
    }
    this.onCloses.push(cb);
}

SocketWrapper.prototype.send = function(data) {
    if (this.open) {
	// FIXME maybe need btoa here?
	//console.log("Sending: ", data);
	this.socket.send(JSON.stringify(data));
    } else {
	console.log("Socket not open. Queueing seq#" + data.seq);
	// TODO auto-delete after calling?
	this.queuedData.push(data);
    }
}

SocketWrapper.prototype.close = function() {
    this.socket.close();
}

function RemoteFunction(socket, seq, name, callback, timeoutCallback, expand) {
    this.socket = socket;
    this.seq = seq;
    this.name = name;
    this.timer = null;
    this.callback = callback;
    this.timeoutCallback = timeoutCallback;
    this.completed = false;
    this.boundMethod = null;
    this.expand = expand;
}

RemoteFunction.prototype.listener = function(data) {
    try {
	if (data && "seq" in data) {
	    if (data.seq == this.seq) {
		clearTimeout(this.timer);
		this.complete = true;
		if (this.callback)
		    this.callback(data);

		// if we leave this around we get exponential calls, oops
		var ourIndex = this.socket.onMessages.indexOf(this.boundMethod);
		delete this.socket.onMessages[ourIndex];
	    }
	}
    } catch (e) {
	console.log("Data is", data);
	console.log(e);
    }
};

RemoteFunction.prototype.call = function(kwargs) {
    if (!kwargs) kwargs = {};
    var data = {
	"seq": this.seq,
	"op": this.name,
	"args": Array.prototype.slice.call(arguments, 1),
	"kwargs": kwargs
    };

    // javascript is stupid
    var theese = this;

    this.boundMethod = function(data){theese.listener(data);};
    this.socket.addOnMessage(this.boundMethod);

    this.socket.send(data);
    // All functions will have a 5 second timeout I guess
    var rf = this;
    if (this.callback) {
	this.timer = setTimeout(function() {
	    console.log("Call (seq#" + theese.seq + ") timed out.");
	    if (rf.timeoutCallback) {
		rf.timeoutCallback();
	    }
	}, 5000);
    }
}

function Client(host, port, path, doneCB) {
    this.id = null; // This will be updated when connection is successful
    this.socket = null;
    this.seq = Math.floor(Math.random() * 9007199254740992);
    this.doneCB = doneCB;
    this.listeners = {};

    this.reconnect = true;
    this.reconnectAttempts = 0;
    this.reconnectWait = 1000;
    this.reconnectTimer = -1;
    this.init(host, port, path);
}

Client.prototype.doReconnectInterval = function(host, port, path) {
    var client = this;
    if (this.reconnect && !this.socket.open && this.socket.closed) {
	this.socket.wrap(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));

	console.log("Trying again in " + (this.reconnectWait/1000) + "s...");
	this.reconnectTimer = setTimeout(function() {
	    client.doReconnectInterval(host, port, path);
	}, this.reconnectWait);

	this.reconnectAttempts++;

	if (this.reconnectAttempts > 5 && this.reconnectAttempts <= 13)
	    this.reconnectWait *= 2;
    } else if (this.socket.open && !this.socket.closed) {
	console.log("Reconnected!");
    }
};

Client.prototype.startReconnect = function(host, port, path) {
    var client = this;
    if (client.reconnect && client.reconnectAttempts == 0) {
	this.doReconnectInterval(host, port, path);
    }
};

Client.prototype.init = function(host, port, path) {
    if (this.socket) this.socket.close();
    this.socket = new SocketWrapper(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));
    var client = this;
 
   var addReconnector = function(host, port, path) {
	client.socket.addOnClose(function(evt) {
	    if (evt && evt.code == 1001) {
		console.log("Server has closed! Will not reconnect.");
	    } else {
		client.startReconnect(host, port, path);
	    }
	});
    };
    addReconnector(host, port, path);

    this.socket.addOnOpen(function() {
	if (client.reconnectTimer != -1) {
	    clearTimeout(client.reconnectTimer);
	    client.reconnectTimer = -1;
	    client.reconnectAttempts = 0;
	    client.reconnectWait = 1000;
	}
	if (client.doneCB) {
	    client.doneCB();
	    client.doneCB = null;
	}
    });
};

Client.prototype.call = function(name, extras) {
    // Extras should be an object, e.g.:
    // client.call("SharedClientDataStore__get", ["SharedClientDataStore", 0],
    //           { args: ["test"],
    //             kwargs: {default: "unknown"},
    //             callback: function(data) {alert(data.result);}
    //           }
    // );
    var args = [], kwargs = {}, callback, timeout = null;
    var expand = false;
    if (extras && 'args' in extras) args = extras.args;
    if (extras && 'kwargs' in extras) kwargs = extras.kwargs;
    if (extras && 'callback' in extras) callback = extras.callback;
    if (extras && 'expand' in extras) expand = extras['expand'];
    if (extras && 'timeout' in extras) timeout = extras['timeout'];

    this.seq += 1;
    var tmpSeq = this.seq;
    var rf = new RemoteFunction(this.socket, tmpSeq, name, callback, timeout, expand);
    var newArgs = [kwargs].concat(args);
    rf.call.apply(rf, newArgs);
};

Client.prototype.quit = function() {
    console.log("Quitting");
    this.reconnect = false;
    this.socket.close();
}
