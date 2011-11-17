#!/usr/bin/env python

usage = """
mpris-remote, written by Nick Welch <nick@incise.org> in 2008-2011.
Homepage: http://incise.org/mpris-remote.html
No copyright. This work is dedicated to the public domain.
For full details, see http://creativecommons.org/publicdomain/zero/1.0/

USAGE: mpris-remote [command [args to command]]

COMMANDS:

  [no command]         prints a display of current player status, song playing,
                       etc.

  prev[ious]           go to previous track
  next                 go to next track
  stop                 stop playback
  play                 start playback
  pause                pause playback

  trackinfo            print metadata for current track
  trackinfo <track#>   print metadata for given track
  trackinfo '*'        print metadata for all tracks

  volume               print volume
  volume <0..100>      set volume

  repeat <true|false>  set current track repeat on or off

  loop                 prints whether or not player will loop track list at end
  loop <true|false>    sets whether or not player will loop track list at end

  random               prints whether or not player will play randomly/shuffle
  random <true|false>  sets whether or not player will play randomly/shuffle

  addtrack <uri>       add track at specified uri
                         (valid file types/protocols dependent on player)
  addtrack <uri> true  add track at specified uri and start playing it now
                         a uri can also be "-" which will read in filenames
                         on stdin, one per line.  (this applies to both
                         variants of addtrack.  the "playnow" variant will
                         add+play the first track and continue adding the rest.)
  deltrack <track#>    delete specified track
  clear                clear playlist

  position             print position within current track
  seek <time>          seek to position in current track
                         supported time formats:
                         hh:mm:ss.ms | mm:ss.ms | ss | ss.ms | .ms
                         hh:mm:ss    |    hh:mm | x% | x.x[x[x]...]%
                         all are negatable to compute from end of track,
                         e.g. -1:00.  the "ss" format can be >60 and the ".ms"
                         format can be >1000.
                         <actually all of that is a lie -- right now you can
                          only pass in an integer as milliseconds>

  tracknum             print track number of current track
  numtracks            print total number of tracks in track list

  playstatus           print whether the player is playing, paused, or stopped,
                       and print the random, repeat, and loop settings

  identity             print identity of player (e.g. name and version)
  quit                 cause player to exit

ENVIRONMENT VARIABLES:

  MPRIS_REMOTE_PLAYER
    If unset or set to "*", mpris-remote will communicate with the first player
    it finds registered under "org.mpris.*" through D-BUS.  If you only have one
    MPRIS-compliant player running, then this will be fine.  If you have more
    than one running, you will want to set this variable to the name of the
    player you want to connect to.  For example, if set to foo, it will try to
    communicate with the player at "org.mpris.foo" and will fail if nothing
    exists at that name.

NOTES:

  track numbers when used or displayed by commands always begin at zero, but
  the informational display when mpris-remote is called with no arguments
  starts them at one.  (track "1/2" being the last track would make no sense.)
"""

import os, sys, re, time, urllib2, dbus

org_mpris_re = re.compile('^org\.mpris\.([^.]+)$')

class BadUserInput(Exception):
    pass

# argument type/content validity checkers

class is_int(object):
    @staticmethod
    def type_desc(remote):
        return 'an integer'

    def __init__(self, remote, arg):
        int(arg)

class is_boolean(object):
    @staticmethod
    def type_desc(remote):
        return 'a boolean'

    def __init__(self, remote, arg):
        if arg not in ('true', 'false'):
            raise ValueError

class is_zero_to_100(object):
    @staticmethod
    def type_desc(remote):
        return 'an integer within [0..100]'

    def __init__(self, remote, arg):
        if not 0 <= int(arg) <= 100:
            raise ValueError

class is_track_num(object):
    @staticmethod
    def type_desc(remote):
        if remote.tracklist_len > 0:
            return 'an integer within [0..%d] (current playlist size is %d)' % (remote.tracklist_len-1, remote.tracklist_len)
        elif remote.tracklist_len == 0:
            return 'an integer within [0..<tracklist length>], ' \
                        'although the current track list is empty, so ' \
                        'no track number would currently be valid'
        else:
            return 'an integer within [0..<tracklist length>] (current tracklist length is unavailable)'

    def __init__(self, remote, arg):
        int(arg)
        if remote.tracklist_len == -1:
            return # not much we can do; just assume it's okay to pass along
        if not 0 <= int(arg) <= remote.tracklist_len-1:
            raise ValueError

class is_track_num_or_star(object):
    @staticmethod
    def type_desc(remote):
        return is_track_num.type_desc(remote) + "\n\nOR a '*' to indicate all tracks"

    def __init__(self, remote, arg):
        if arg != '*':
            is_track_num(remote, arg)

class is_valid_uri(object):
    @staticmethod
    def type_desc(remote):
        return 'a valid URI (media file, playlist file, stream URI, or directory)'

    def __init__(self, remote, arg):
        if arg.startswith('file://'):
            arg = urllib2.unquote(arg.partition('file://')[2])

        # arbitrary uri, don't wanna hardcode possible protocols
        if re.match(r'\w+://.*', arg):
            return

        if os.path.isfile(arg) or os.path.isdir(arg) or arg == '-':
            return

        raise ValueError

# wrong argument(s) explanation decorators

def explain_numargs(*forms):
    def wrapper(meth):
        def new(self, *args):
            if len(args) not in forms:
                s = ' or '.join(map(str, forms))
                raise BadUserInput("%s takes %s argument(s)." % (meth.func_name, s))
            return meth(self, *args)
        new.func_name = meth.func_name
        return new
    return wrapper

def explain_argtype(i, typeclass, optional=False):
    def wrapper(meth):
        def new(remote_self, *args):
            if not optional or len(args) > i:
                try:
                    typeclass(remote_self, args[i])
                except:
                    raise BadUserInput("argument %d to %s must be %s." % (i+1, meth.func_name, typeclass.type_desc(remote_self)))
            return meth(remote_self, *args)
        new.func_name = meth.func_name
        return new
    return wrapper

# and the core

def format_time(rawms):
    min = rawms / 1000 / 60
    sec = rawms / 1000 % 60
    ms = rawms % 1000
    return "%d:%02d.%03d" % (min, sec, ms)


def playstatus_from_int(n):
    return ['playing', 'paused', 'stopped'][n]

class NoTrackCurrentlySelected(Exception):
    pass

def format_metadata(dct):
    lines = []
    for k in sorted(dct.keys()):
        v = dct[k]

        if k == 'audio-bitrate':
            v = float(v) / 1000
            if v % 1 < 0.01:
                v = int(v)
            else:
                v = "%.3f" % v

        if k == 'time':
            v = "%s (%s)" % (v, format_time(int(v) * 1000).split('.')[0])

        if k == 'mtime':
            v = "%s (%s)" % (v, format_time(int(v)))

        lines.append("%s: %s" % (k, v))
    return '\n'.join(lines) + '\n'

class RequestedPlayerNotRunning(Exception):
    pass

class NoPlayersRunning(Exception):
    pass

class MPRISRemote(object):

    def __init__(self):
        self.bus = dbus.SessionBus()
        self.players_running = [ name for name in self.bus.list_names() if org_mpris_re.match(name) ]

    def find_player(self, requested_player_name):
        if not self.players_running:
            raise NoPlayersRunning()

        if requested_player_name == '*':
            self.player_name = org_mpris_re.match(self.players_running[0]).group(1)
        else:
            if 'org.mpris.%s' % requested_player_name not in self.players_running:
                raise RequestedPlayerNotRunning()
            self.player_name = requested_player_name

        root_obj      = self.bus.get_object('org.mpris.%s' % self.player_name, '/')
        player_obj    = self.bus.get_object('org.mpris.%s' % self.player_name, '/Player')
        tracklist_obj = self.bus.get_object('org.mpris.%s' % self.player_name, '/TrackList')

        self.root      = dbus.Interface(root_obj,      dbus_interface='org.freedesktop.MediaPlayer')
        self.player    = dbus.Interface(player_obj,    dbus_interface='org.freedesktop.MediaPlayer')
        self.tracklist = dbus.Interface(tracklist_obj, dbus_interface='org.freedesktop.MediaPlayer')

        try:
            self.tracklist_len = self.tracklist.GetLength()
        except dbus.exceptions.DBusException:
            # GetLength() not supported by player (BMPx for example)
            self.tracklist_len = -1


    def _possible_names(self):
        return [ name for name in self.bus.list_names() if org_mpris_re.match(name) ]

    # commands

    # root

    @explain_numargs(0)
    def identity(self):
        print self.root.Identity()

    @explain_numargs(0)
    def quit(self):
        self.root.Quit()

    # player

    @explain_numargs(0)
    def prev(self):
        self.player.Prev()

    @explain_numargs(0)
    def previous(self):
        self.player.Prev()

    @explain_numargs(0)
    def next(self):
        self.player.Next()

    @explain_numargs(0)
    def stop(self):
        self.player.Stop()

    @explain_numargs(0)
    def play(self):
        self.player.Play()

    @explain_numargs(0)
    def pause(self):
        self.player.Pause()

    @explain_numargs(0, 1)
    @explain_argtype(0, is_zero_to_100, optional=True)
    def volume(self, vol=None):
        if vol is not None:
            self.player.VolumeSet(int(vol))
        else:
            print self.player.VolumeGet()

    @explain_numargs(0)
    def position(self):
        print format_time(self.player.PositionGet())

    @explain_numargs(1)
    @explain_argtype(0, is_int)
    def seek(self, pos):
        self.player.PositionSet(int(pos))

    @explain_numargs(1)
    @explain_argtype(0, is_boolean)
    def repeat(self, on):
        if on == 'true':
            self.player.Repeat(True)
        elif on == 'false':
            self.player.Repeat(False)

    @explain_numargs(0)
    def playstatus(self):
        status = self.player.GetStatus()
        yield ("playing: %s\n" % playstatus_from_int(status[0])
             + "random/shuffle: %s\n" % ("true" if status[1] else "false")
             + "repeat track: %s\n" % ("true" if status[2] else "false")
             + "repeat list: %s\n" % ("true" if status[3] else "false"))

    @explain_numargs(0, 1)
    @explain_argtype(0, is_track_num_or_star, optional=True)
    def trackinfo(self, track=None):
        if track == '*':
            for i in range(self.tracklist_len):
                meta = self.tracklist.GetMetadata(i)
                if meta is not None:
                    yield format_metadata(self.tracklist.GetMetadata(i))
                    yield '\n'
        else:
            if track is not None:
                meta = self.tracklist.GetMetadata(int(track))
            else:
                meta = self.player.GetMetadata()
                if meta is None:
                    raise NoTrackCurrentlySelected()
            yield format_metadata(meta)

    # tracklist

    @explain_numargs(0)
    def clear(self):
        self.player.Stop()
        for i in range(self.tracklist.GetLength()):
            self.tracklist.DelTrack(0)

    @explain_numargs(1)
    @explain_argtype(0, is_track_num)
    def deltrack(self, pos):
        self.tracklist.DelTrack(int(pos))

    @explain_numargs(1, 2)
    @explain_argtype(0, is_valid_uri)
    @explain_argtype(1, is_boolean, optional=True)
    def addtrack(self, uri, playnow='false'):
        playnow = playnow == 'true'
        if uri == '-':
            for i, line in enumerate(sys.stdin):
                path = line.rstrip('\r\n')

                if not path.strip():
                    continue

                if not (os.path.isfile(path) or os.path.isdir(path)):
                    raise BadUserInput('not a file or directory: %s' % path)

                if playnow and i == 0:
                    self.tracklist.AddTrack(path, True)
                else:
                    self.tracklist.AddTrack(path, False)
        else:
            self.tracklist.AddTrack(uri, playnow)

    @explain_numargs(0)
    def tracknum(self):
        yield str(self.tracklist.GetCurrentTrack()) + '\n'

    @explain_numargs(0)
    def numtracks(self):
        yield str(self.tracklist.GetLength()) + '\n'

    @explain_numargs(0, 1)
    @explain_argtype(0, is_boolean, optional=True)
    def loop(self, on=None):
        if on == 'true':
            self.tracklist.SetLoop(True)
        elif on == 'false':
            self.tracklist.SetLoop(False)
        else:
            try:
                status = self.player.GetStatus()
            except dbus.exceptions.DBusException:
                print >>sys.stderr, "Player does not support checking loop status."
            else:
                yield ("true" if status[3] else "false") + '\n'

    @explain_numargs(0, 1)
    @explain_argtype(0, is_boolean, optional=True)
    def random(self, on=None):
        if on == 'true':
            self.tracklist.SetRandom(True)
        elif on == 'false':
            self.tracklist.SetRandom(False)
        else:
            try:
                status = self.player.GetStatus()
            except dbus.exceptions.DBusException:
                print >>sys.stderr, "Player does not support checking random status."
            else:
                yield ("true" if status[1] else "false") + '\n'

    def verbose_status(self):
        # to be compatible with a wide array of implementations (some very
        # incorrect/incomplete), we have to do a LOT of extra work here.

        output = ''

        try:
            status = self.player.GetStatus()
        except dbus.exceptions.DBusException:
            status = None

        try:
            status[0] # dragon player returns a single int, which is wrong
        except TypeError:
            status = None

        try:
            curtrack = self.tracklist.GetCurrentTrack()
        except dbus.exceptions.DBusException:
            curtrack = None

        try:
            pos = self.player.PositionGet()
        except dbus.exceptions.DBusException:
            pos = None

        try:
            meta = self.player.GetMetadata()
            meta = dict(meta) if meta else {}
        except dbus.exceptions.DBusException:
            meta = {}

        if 'mtime' in meta:
            mtime = int(meta['mtime'])
            if abs(mtime - time.time()) < 60*60*24*365*5:
                # if the mtime is within 5 years of right now, which would mean the
                # song is thousands of hours long, then i'm gonna assume that the
                # player is incorrectly using this field for the file's mtime, not
                # the song length. (bmpx does this as of january 2008)
                del meta['mtime']

                # and also, if we know it's bmp, then we can swipe the time field
                if self.player_name == 'bmp':
                    meta['mtime'] = meta['time'] * 1000

        have_status = (status is not None)
        have_curtrack = (curtrack is not None)
        have_listlen = (self.tracklist_len >= 0)
        have_player_info = (have_status or have_curtrack or have_listlen)

        have_pos = (pos is not None)
        have_mtime = ('mtime' in meta)
        have_tracknum = ('tracknumber' in meta)
        have_song_info = (have_pos or have_mtime or have_tracknum)

        ##

        if have_player_info:
            output += '['

        if have_status:
            output += "%s" % playstatus_from_int(status[0])
            if have_curtrack:
                output += ' '

        if have_curtrack:
            output += str(curtrack+1)
            if have_listlen:
                output += '/'

        if have_listlen:
            output += str(self.tracklist_len)

        if have_player_info:
            output += ']'

        ##

        if have_player_info and have_song_info:
            output += ' '

        ##

        if have_pos or have_mtime:
            output += '@ '
            if have_pos:
                output += format_time(pos).split('.')[0]
            elif have_mtime:
                output += '?'

            if have_mtime:
                output += '/'
                output += format_time(meta['mtime']).split('.')[0]

        if have_tracknum:
            output += ' - #%s' % meta['tracknumber']

        if have_player_info or have_song_info:
            output += '\n'

        ##

        if 'artist' in meta:
            output += '  artist: ' + meta['artist'] + '\n'
        if 'title' in meta:
            output += '  title: ' + meta['title'] + '\n'
        if 'album' in meta:
            output += '  album: ' + meta['album'] + '\n'

        if have_status:
            output += '[repeat %s] [random %s] [loop %s]\n' % (
                "on" if status[2] else "off",
                "on" if status[1] else "off",
                "on" if status[3] else "off",
            )

        return output


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help', '-?'):
        print usage
        raise SystemExit(0)

    player_name = os.environ.get('MPRIS_REMOTE_PLAYER', '*')
    remote = MPRISRemote()

    try:
        remote.find_player(player_name)
    except RequestedPlayerNotRunning, e:
        print >>sys.stderr, 'Player "%s" is not running, but the following players were found:' % player_name
        for n in remote.players_running:
            print >>sys.stderr, "    %s" % n.replace("org.mpris.", "")
        print >>sys.stderr, 'If you meant to use one of those players, ' \
                            'set $MPRIS_REMOTE_PLAYER accordingly.'
        raise SystemExit(1)
    except NoPlayersRunning:
        print >>sys.stderr, "No MPRIS-compliant players found running."
        raise SystemExit(1)

    import locale
    encoding = sys.stdout.encoding or locale.getpreferredencoding() or 'ascii'

    if len(sys.argv) == 1:
        method_name = 'verbose_status'
        args = []
    else:
        method_name = sys.argv[1]
        args = sys.argv[2:]

    try:
        output_generator = getattr(remote, method_name)(*args) or []
        for chunk in output_generator:
            sys.stdout.write(chunk.encode(encoding, 'replace'))
    except BadUserInput, e:
        print >>sys.stderr, e
        raise SystemExit(1)
    except NoTrackCurrentlySelected:
        print >>sys.stderr, "No track is currently selected."
    except KeyboardInterrupt:
        raise SystemExit(2)

