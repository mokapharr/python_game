import pyglet
import pygletreactor
pygletreactor.install()
from twisted.internet import reactor
from menu.window_manager import WindowManager
from network_utils.clientclass import Client

window = pyglet.window.Window(1280, 720, vsync=True)
#window.set_mouse_visible(True)
window.set_exclusive_mouse(True)
WindowManager = WindowManager(window)
# load and init different modules
fps = pyglet.clock.ClockDisplay()
fps_limit = 120.
#pyglet.clock.set_fps_limit(fps_limit)
client = Client()
WindowManager.register(client.get_input, 'input')
client.register(WindowManager.receive_events, 'serverdata')


def update(dt):
    WindowManager.update(dt)
pyglet.clock.schedule(update)


@window.event
#draw
def on_draw():
    window.clear()
    pyglet.gl.glClearColor(0, .0, 0, 1)
    pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
    WindowManager.draw()
    fps.draw()

reactor.listenUDP(8001, client)
client.start_connection()
reactor.run(call_interval=1./fps_limit)
