from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

import json

import time
import sys
import os

from commands import Commander, schedule_standup


class JSONStore(dict):
    """
    Blocking and crappy
    """
    def __init__(self, path):
        self._path = path
        self._cache = {}
        self._fill_cache()

    def __getitem__(self, name):
        return self._cache[name]

    def __setitem__(self, name, value):
        self._cache[name] = value
        self._flush_cache()

    def __delitem__(self, name):
        del self._cache[name]
        self._flush_cache()

    def __contains__(self, name):
        return self._cache.__contains__(name)

    def flush(self):
        self._flush_cache()

    def _open(self, mode):
        return os.fdopen(os.open(self._path, os.O_RDWR | os.O_EXLOCK | os.O_CREAT), mode)

    def _fill_cache(self):
        log.msg('Loading conf from "%s"' % (self._path))
        f = None
        try:
            f = self._open('r')
            conf = f.read()
            self._cache = json.loads(conf)
        except Exception as e:
            log.msg('Loading conf from "%s" failed: %s' % (self._path, e))
            if reactor.running:
                reactor.stop()
        finally:
            if f:
                f.close()

    def _flush_cache(self):
        log.msg('Flushing conf to "%s"' % (self._path))
        f = None
        try:
            conf = json.dumps(self._cache, sort_keys=True, indent=4)
            f = self._open('w')
            f.truncate()
            f.write(conf)
        except Exception as e:
            log.msg('Writing conf to "%s" failed: %s' % (self._path, e))
            if reactor.running:
                reactor.stop()
        finally:
            if f:
                f.close()


class StandupBot(irc.IRCClient):

    @property
    def config(self):
        return self.factory.config

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg("[connected at %s]" % time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        log.msg("[disconnected at %s]" % time.asctime(time.localtime(time.time())))

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel, data in self.config['channels'].iteritems():
            self.join(str(channel))
            schedule_standup(self, channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        log.msg("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        log.msg("<%s> %s" % (user, msg))

        if channel == self.nickname:
            self.msg(user, 'PRVMSG not supported, talk in the channel')
            return  # don't support PM

        if msg.startswith(self.nickname + ":"):
            msg = msg[len(self.nickname + ":"):]
            msg = msg.strip()

            self.commander.run_command(self, user, channel, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        log.msg("* %s %s" % (user, msg))

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        log.msg("%s is now known as %s" % (old_nick, new_nick))

    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return self.nickname + '^'


class StandupBotFactory(protocol.ClientFactory):

    def __init__(self, config):
        self.config = config

    def buildProtocol(self, addr):
        p = StandupBot()
        p.factory = self
        p.nickname = str(self.config['nick'])
        p.commander = Commander()
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


def _validate_config(config):
    valid = True
    msg = []
    if 'host' not in config:
        valid = False
        msg.append('host')
    if 'port' not in config:
        valid = False
        msg.append('port')
    if 'nick' not in config:
        valid = False
        msg.append('nick')

    return valid, msg


if __name__ == '__main__':

    # logging
    log.startLogging(sys.stdout)

    # load config
    config = JSONStore('./standupbot-config.json')
    valid, msg = _validate_config(config)
    if not valid:
        log.msg('Invalid config - missing fields: %s' % (', '.join(msg)))
        sys.exit(1)

    # setup bot
    f = StandupBotFactory(config)
    reactor.connectTCP(str(config['host']), config['port'], f)

    # run bot
    reactor.run()
