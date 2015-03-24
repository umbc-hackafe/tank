from __future__ import division, print_function
import sys, time, threading, json

def imports():
    global cherrypy
    import cherrypy

    global ws4py
    import ws4py.server.cherrypyserver
    import ws4py.websocket

FILES = {
    "index": "./inputdrivers/websocket.html"
}
CACHE = {}
MSG_TIMEOUT = 1.0

def get_content(name):
    res = CACHE.get(name, None)
    if res:
        return res
    else:
        with open(FILES[name]) as f:
            CACHE[name] = f.read()
        return CACHE[name]

def main(client, args):
    imports()

    cherrypy.config.update({'server.socket_port': 80})
    ws4py.server.cherrypyserver.WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = ws4py.server.cherrypyserver.WebSocketTool()

    def timeout_thread(tank):
        while not tank.terminated:
            tank.check_timeout()
            time.sleep(MSG_TIMEOUT/2)

    class TankWebSocket(ws4py.websocket.EchoWebSocket):
        def check_timeout(self):
            if time.time() - self.last_received > MSG_TIMEOUT:
                client.halt()
                return False
            return True

        def received_message(self, message):
            self.last_received = time.time()
            action = json.loads(message.data)
            path = action["target"].split(".")
            args = action.get("args", [])
            kwargs = action.get("kwargs", {})

            with client.lock:
                target = client
                for elm in path:
                    if hasattr(target, elm):
                        target = getattr(target, elm)
                    else:
                        self.send(json.dumps({"error": "{} does not have attirbute {}".format(target, elm)}))

                try:
                    res = target(*args, **kwargs)
                    if res:
                        self.send(json.dumps({"result": res}))
                except RuntimeError as e:
                    self.send(json.dumps({"error": e}))

        def opened(self):
            self.last_received = time.time()
            self.ping_waiter = Thread(target=timeout_thread, args=(self,))
            self.ping_waiter.start()

        def closed(self, code, reason=None):
            client.halt()

    class Root(object):
        @cherrypy.expose
        def index(self):
            return get_content("index")

        @cherrypy.expose
        def ws(self):
            handler = cherrypy.request.ws_handler

    cherrypy.quickstart(Root(), config={
        '/ws': {'tools.websocket.on': True,
                'tools.websocket.handler_cls': TankWebSocket}})
