#!/usr/bin/env python

import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mock'))

# the mprisremote.py in mock/ is just a symlink to mpris-remote.  this is so we
# can import it as a module.
import dbus, mprisremote

class MPRISRemoteTests(unittest.TestCase):
    def setUp(self):
        # often times we want to call this several times within one test, but
        # at the very least, we will always want to call it once at the
        # beginning.
        dbus.start_mocking('foo')

    def callCommand(self, command, *args):
        dbus.start_mocking('foo')
        r = mprisremote.MPRISRemote()
        r.find_player('foo')
        getattr(r, command)(*args)

    def assertCalled(self, methodcalls):
        # GetLength always gets called on startup (not ideal...)
        methodcalls = [('/TrackList', 'GetLength')] + list(methodcalls)
        self.assertEquals(list(methodcalls), dbus._method_calls)

    def assertCallDbusActivity(self, command, args, *expected_method_calls):
        self.callCommand(command, *args)
        self.assertCalled(expected_method_calls)

    def assertBadInput(self, command, *args):
        self.assertRaises(mprisremote.BadUserInput, self.callCommand, command, *args)

    def test_basic_commands(self):
        self.assertCallDbusActivity('identity', [], ('/', 'Identity'))
        self.assertCallDbusActivity('quit',     [], ('/', 'Quit'))
        self.assertCallDbusActivity('prev',     [], ('/Player', 'Prev'))
        self.assertCallDbusActivity('previous', [], ('/Player', 'Prev'))
        self.assertCallDbusActivity('next',     [], ('/Player', 'Next'))
        self.assertCallDbusActivity('stop',     [], ('/Player', 'Stop'))
        self.assertCallDbusActivity('play',     [], ('/Player', 'Play'))
        self.assertCallDbusActivity('pause',    [], ('/Player', 'Pause'))

    def test_volume_set(self):
        self.assertCallDbusActivity('volume', ['0'], ('/Player', 'VolumeSet', 0))
        self.assertCallDbusActivity('volume', ['1'], ('/Player', 'VolumeSet', 1))
        self.assertCallDbusActivity('volume', ['50'], ('/Player', 'VolumeSet', 50))
        self.assertCallDbusActivity('volume', ['99'], ('/Player', 'VolumeSet', 99))
        self.assertCallDbusActivity('volume', ['100'], ('/Player', 'VolumeSet', 100))
        self.assertBadInput('volume', '-1')
        self.assertBadInput('volume', '101')
        self.assertBadInput('volume', '22359871')
        self.assertBadInput('volume', '0xff')
        self.assertBadInput('volume', 'loud')
        self.assertBadInput('volume', '1', '2')

    def test_seek(self):
        self.assertCallDbusActivity('seek', ['0'], ('/Player', 'PositionSet', 0))
        self.assertCallDbusActivity('seek', ['1'], ('/Player', 'PositionSet', 1))
        self.assertCallDbusActivity('seek', ['2123123123'], ('/Player', 'PositionSet', 2123123123))
        #self.assertBadInput('seek', '-1') what does the spec say about negative numbers?
        self.assertBadInput('seek', 'a')
        self.assertBadInput('seek', '0x0')
        self.assertBadInput('seek', '0\na')

    def test_extra_arg(self):
        self.assertBadInput('identity', 'x')

    def test_print_verbose_status_nothing(self):
        r = mprisremote.MPRISRemote()
        r.find_player('foo')
        self.assertEquals('', r.verbose_status())

    def test_print_verbose_status_typical(self):
        dbus.mock_method('/TrackList', 'GetLength', lambda: 4)
        dbus.mock_method('/Player', 'GetStatus', lambda: [0, 1, 0, 1])
        dbus.mock_method('/TrackList', 'GetCurrentTrack', lambda: 2)
        dbus.mock_method('/Player', 'PositionGet', lambda: 89147)
        dbus.mock_method('/Player', 'GetMetadata', lambda: {
            'audio-bitrate': 289671,
            'time': 143,
            'mtime': 143201,
            'album': 'This is the Album',
            'artist': 'An Artist',
            'date': '1997',
            'length': 143201,
            'location': 'file:///home/me/Music/An%20Artist/This%20is%20the%20Album%20I_%201974-1980/An Artist%20-%2003%20-%20Yeah%20Whatever.mp3',
            'title': 'Yeah Whatever',
            'trackid': '00000000-1111-2222-3333-444444444444',
            'tracknumber': '3',
        })
        expected_output = (
            '[playing 3/4] @ 1:29/2:23 - #3\n'
            '  artist: An Artist\n'
            '  title: Yeah Whatever\n'
            '  album: This is the Album\n'
            '[repeat off] [random on] [loop on]\n')
        r = mprisremote.MPRISRemote()
        r.find_player('foo')
        self.assertEquals(expected_output, r.verbose_status())

    def test_playstatus(self):
        dbus.mock_method('/Player', 'GetStatus', lambda: [0, 1, 0, 1])
        expected_output = ("playing: playing\n"
              + "random/shuffle: true\n"
              + "repeat track: false\n"
              + "repeat list: true\n")
        r = mprisremote.MPRISRemote()
        r.find_player('foo')
        self.assertEquals(expected_output, r.playstatus())

    def test_find_player_success(self):
        r = mprisremote.MPRISRemote()
        r.find_player('foo')
        self.assertEquals(['org.mpris.foo'], r.players_running)

    def test_find_player_requested_not_running(self):
        r = mprisremote.MPRISRemote()
        self.assertRaises(mprisremote.RequestedPlayerNotRunning, r.find_player, 'bar')
        self.assertEquals(['org.mpris.foo'], r.players_running)

    def test_find_player_none_running(self):
        dbus.start_mocking(None)
        r = mprisremote.MPRISRemote()
        self.assertRaises(mprisremote.NoPlayersRunning, r.find_player, 'foo')
        self.assertEquals([], r.players_running)

if __name__ == '__main__':
    unittest.main()
