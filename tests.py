#!/usr/bin/env python

import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mock'))

# the mprisremote.py in mock/ is just a symlink to mpris-remote.  this is so we
# can import it as a module.
import dbus, mprisremote

class MPRISRemoteTests(unittest.TestCase):
    def callCommand(self, command, *args):
        dbus.start_mocking('foo')
        r = mprisremote.MPRISRemote()
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

if __name__ == '__main__':
    unittest.main()
