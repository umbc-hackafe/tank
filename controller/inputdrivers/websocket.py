from __future__ import division, print_function
import sys, time, threading, json, os, subprocess, httplib

def imports():
    global cherrypy
    import cherrypy

    global ws4py
    import ws4py.server.cherrypyserver
    import ws4py.websocket

FILES = {
    "index": os.path.join(os.path.dirname(os.path.abspath(__file__)), "websocket", "index.html"),
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

    cherrypy.config.update({'server.socket_port': 80,
                            'server.socket_host': '0.0.0.0'})
    ws4py.server.cherrypyserver.WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = ws4py.server.cherrypyserver.WebSocketTool()

    def timeout_thread(tank):
        while not tank.terminated and not getattr(tank, 'stopnow', False):
            tank.check_timeout()
            time.sleep(MSG_TIMEOUT/2)

    class TankWebSocket(ws4py.websocket.WebSocket):
        def check_timeout(self):
            if time.time() - self.last_received > MSG_TIMEOUT:
                try:
                    client.halt()
                except httplib.CannotSendRequest, httplib.ResponseNotReady:
                    pass
                return False
            return True

        def received_message(self, message):
            self.last_received = time.time()
            action = json.loads(message.data)
            seq = action.get("seq", -1)
            path = action["op"].split(".")
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
                        try:
                            self.send(json.dumps({"result": res, "seq": seq}))
                        except TypeError:
                            self.send(json.dumps({"result": None, "seq": seq}))
                except RuntimeError as e:
                    self.send(json.dumps({"error": str(e), "seq": seq}))

        def opened(self):
            self.last_received = time.time()
            self.ping_waiter = threading.Thread(target=timeout_thread, args=(self,))
            self.ping_waiter.daemon = True
            self.ping_waiter.start()

        def closed(self, code, reason=None):
            client.halt()
            self.stopnow = True

    def espeak(text):
        es = subprocess.Popen(["espeak", "--stdout", text], stdout=subprocess.PIPE)
        ap = subprocess.Popen(["aplay", "-"], stdin=es.stdout, stdout=subprocess.PIPE)
        es.stdout.close()
        ap.communicate()

    class Root(object):
        @cherrypy.expose
        def index(self):
            return get_content("index")

        @cherrypy.expose
        def speak(self, text='test'):
            threading.Thread(target=espeak, args=(text,)).start()

        @cherrypy.expose
        def sound(self, name='menu5'):
            threading.Thread(target=lambda n:subprocess.call(['aplay', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'websocket', 'sounds', n) + ".wav"]), args=(name,)).start()

        @cherrypy.expose
        def ws(self):
            handler = cherrypy.request.ws_handler

    cherrypy.quickstart(Root(), config={
        '/ws': {'tools.websocket.on': True,
                'tools.websocket.handler_cls': TankWebSocket},
        '/' : { 'tools.staticdir.root': os.path.dirname(os.path.abspath(__file__)),
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'websocket'}})
