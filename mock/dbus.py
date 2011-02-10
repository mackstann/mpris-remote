_current_player_name = None
_method_calls = []

def start_mocking(player_name):
    global _current_player_name
    _current_player_name = player_name

class MockFailure(Exception):
    pass

class _ProxyObject(object):
    def __init__(self, path):
        self.path = path

class SessionBus(object):
    def __init__(self):
        if _current_player_name is None:
            raise MockFailure("start_mocking() was not called.")

    def get_object(self, bus_name, object_path):
        if bus_name != 'org.mpris.' + _current_player_name:
            raise MockFailure("requested player name is wrong")
        if object_path not in ('/', '/Player', '/TrackList'):
            raise MockFailure("requested object path is wrong")
        return _ProxyObject(object_path)

    def list_names(self):
        return ['org.mpris.' + _current_player_name]

class Interface(object):
    def __init__(self, obj, dbus_interface):
        if dbus_interface != 'org.freedesktop.MediaPlayer':
            raise MockFailure("dbus_interface is wrong")
        self.obj = obj

    def __getattr__(self, methodname):
        def recorder(*args):
            _method_calls.append((self.obj.path, methodname) + args)
        return recorder

class exceptions(object):
    class DBusException(Exception):
        pass
