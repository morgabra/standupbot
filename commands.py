from twisted.python import log
from twisted.internet import reactor

import re
import time
import random

TIME_REGEX = re.compile('[MTWRF]@\d\d:\d\d')


class GooglePlus(object):

    standup_type = 'googleplus'

    @classmethod
    def run(cls, client, channel):
        users = client.config['channels'][channel]['users']
        client.msg(str(channel), str('%s: it\'s standup time!' % (': '.join(users))))
        client.msg(str(channel), str('hangout link: https://hangoutsapi.talkgadget.google.com/hangouts?authuser=0&gid=%s' % (client.config['google-hangout-gid'])))


class IRC(object):

    standup_type = 'irc'

    @classmethod
    def cancel(cls, client, channel):
        log.msg('resetting standup state in %s' % channel)
        client.config['channels'][channel]['active'] = False
        client.config['channels'][channel]['started_at'] = None
        client.config['channels'][channel]['current_user'] = None
        users = client.config['channels'][channel]['users']
        new_users = {}
        for user, active in users.items():
            new_users[user] = False
        client.config['channels'][channel]['users'] = new_users
        client.config.flush()

    @classmethod
    def run(cls, client, channel):
        cls.cancel(client, channel)
        users = client.config['channels'][channel]['users']
        user = random.choice(list(users.keys()))
        client.config['channels'][channel]['started_at'] = time.time()
        client.config['channels'][channel]['current_user'] = user
        client.config['channels'][channel]['active'] = True
        client.config.flush()
        client.msg(str(channel), str('%s: it\'s standup time!' % (': '.join(users))))
        client.msg(str(channel), str('%s: you\'re up first (remember to tell me \'next\' when you are done)' % user))

    @classmethod
    def check(cls, client, channel):
        active = client.config['channels'][channel]['active']
        users = client.config['channels'][channel]['users']
        current_user = client.config['channels'][channel]['current_user']

        if active:
            if users[current_user]:
                for user, done in users.items():
                    if not done:
                        client.config['channels'][channel]['current_user'] = user
                        client.msg(str(channel), str('%s: you\'re up next (remember to tell me \'next\' when you are done)' % user))
                        return

        started_at = client.config['channels'][channel]['started_at']
        current_time = time.time()
        time_taken = '%.02f' % ((int(current_time) - started_at) / 60)
        client.msg(str(channel), str('standup DONE! (total time: %s)' % time_taken))
        IRC.cancel(client, channel)


class Join(object):

    command = 'join'

    @classmethod
    def help(cls):
        return 'join <chan>: have the bot join the give channel'

    @classmethod
    def do_command(cls, client, user, channel, args):
        if not args:
            return 'need channel name'

        args = args.strip()
        channel = client.config['channels'].get(args)
        if channel:
            return 'already joined %s' % (args)

        new_channel = {
            "active": False,
            "current_user": None,
            "started_at": None,
            "times": {},
            "users": {}
        }
        client.config['channels'][args] = new_channel
        client.config.flush()
        client.join(str(args))
        reactor.callLater(60, client.commander.check_standup_time, client, args)
        return 'joining %s' % (args)


class Leave(object):

    command = 'leave'

    @classmethod
    def help(cls):
        return 'leave: make the bot leave'

    @classmethod
    def do_command(cls, client, user, channel, args):
        chan = client.config['channels'].get(channel)
        if chan:
            client.leave(channel)
            del client.config['channels'][channel]
            client.config.flush()


class Status(object):

    command = 'status'

    @classmethod
    def help(cls):
        return 'usage: status - shows current standup status'

    @classmethod
    def do_command(cls, client, user, channel, args):
        active = client.config['channels'][channel]['active']

        if active:
            current_user = client.config['channels'][channel]['current_user']
            started_at = client.config['channels'][channel]['started_at']
            current_time = time.time()
            time_taken = '%.02f' % ((int(current_time) - started_at) / 60)
            return 'active standup user: %s total time: %s minutes' % (current_user, time_taken)
        else:
            return 'no active standup'


class Start(object):

    command = 'start'

    @classmethod
    def help(cls):
        return 'usage: start <type> - start an unscheduled standup'

    @classmethod
    def do_command(cls, client, user, channel, args):
        if args == 'googleplus':
            GooglePlus.run(client, channel)
        elif args == 'irc':
            IRC.run(client, channel)


class Reset(object):

    command = 'reset'

    @classmethod
    def help(cls):
        return "usage: reset - reset standup state"

    @classmethod
    def do_command(cls, client, user, channel, args):
        IRC.cancel(client, channel)
        return "current standup is reset"


class Next(object):

    command = 'next'

    @classmethod
    def help(cls):
        return "usage: next - advance to the next person in the standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        active = client.config['channels'][channel]['active']
        if not active:
            return

        current_user = client.config['channels'][channel]['current_user']
        if args == 'force':
            client.config['channels'][channel]['users'][current_user] = True
            client.config.flush()
            IRC.check(client, channel)
        else:
            if current_user == user:
                client.config['channels'][channel]['users'][user] = True
                client.config.flush()
                IRC.check(client, channel)


class List(object):

    command = 'list'

    @classmethod
    def help(cls):
        return "usage: 'list (users, times)' - list users/standup time currently configured"

    @classmethod
    def do_command(cls, client, user, channel, args):
        list_type = args.strip()

        val = client.config['channels'][channel].get(list_type)
        if val == None:
            return cls.help()

        if list_type == 'times':
            val = ["%s (%s)" % (stime, stype) for stime, stype in val.items()]
        else:
            val = ["%s" % user for user, active in val.items()]

        return 'standup %s: %s' % (list_type, ', '.join(val))


class Add(object):

    command = 'add'

    @classmethod
    def help(cls):
        return "usage: 'add (user, time) <argument>' - add user/time to standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        args = args.strip().split(' ', 1)
        if len(args) == 2:
            add_type = args[0] + 's'
            arg = args[1]
        else:
            return cls.help()

        val = client.config['channels'][channel].get(add_type)
        if val == None:
            return cls.help()

        if add_type == 'times':
            arg = arg.strip().split(' ', 1)
            if len(arg) == 2:
                stime = arg[0]
                stype = arg[1]
            else:
                return cls.help()

            if not TIME_REGEX.match(stime):
                return 'times must be of format M/T/W/R/F@00:00 (all times 24hr format and UTC)'
            if not stype in ('googleplus', 'irc'):
                return 'type must be googleplus or irc'

            for ctime, ctype in val.items():
                if ctime == stime:
                    return 'already added %s to %s' % (stime, add_type)

            val[stime] = stype
            client.config['channels'][channel][add_type] = val
            client.config.flush()
            return 'added %s (%s) to %s' % (stime, stype, add_type)

        else:
            if arg in val:
                return 'already added %s to %s' % (arg, add_type)

            val[arg] = False
            client.config['channels'][channel][add_type] = val
            client.config.flush()
            return 'added %s to %s' % (arg, add_type)


class Remove(object):

    command = 'remove'

    @classmethod
    def help(cls):
        return "usage: 'remove (user, time) <argument>' - remove user/time to standup"

    @classmethod
    def do_command(cls, client, user, channel, args):
        args = args.strip().split(' ', 1)
        if len(args) == 2:
            remove_type = args[0] + 's'
            arg = args[1]
        else:
            return cls.help()

        val = client.config['channels'][channel].get(remove_type)
        if val == None:
            return cls.help()

        if remove_type == 'times':
            if not TIME_REGEX.match(arg):
                return 'times must be of format M/T/W/R/F@00:00 (all times 24hr format and UTC)'

            if arg in val:
                stype = val[arg]
                del val[arg]
            client.config['channels'][channel][remove_type] = val
            client.config.flush()
            return 'removed %s (%s) from %s' % (arg, stype, remove_type)

        else:
            if arg in val:
                del val[arg]
            client.config['channels'][channel][remove_type] = val
            client.config.flush()
            return 'removed %s from %s' % (arg, remove_type)


class Commander(object):
    COMMANDS = [List, Add, Remove, Start, Next, Reset, Status, Join, Leave]
    STANDUP_HOOKS = [GooglePlus, IRC]
    WEEKDAY_MAP = {'1': 'M', '2': 'T', '3': 'W', '4': 'R', '5': 'F'}

    def check_standup_time(self, client, channel):
        chan = client.config['channels'].get(channel)
        if not chan:
            log.msg('Channel %s not found in config, skipping standup check' % (channel))
            return

        times = client.config['channels'][channel]['times']
        current_day = time.strftime('%w')
        current_time = time.strftime('%H:%M')

        formatted_time = '%s@%s' % (self.WEEKDAY_MAP[current_day], current_time)
        log.msg('checking if it\'s time for standup in %s (%s)' % (channel, formatted_time))
        run_standup = False

        for standup_time, standup_type in times.items():
            if formatted_time == standup_time:
                run_standup = True

        if run_standup:
            log.msg('it\'s standup time in %s! (%s)' % (channel, standup_type))
            for s in self.STANDUP_HOOKS:
                if standup_type == s.standup_type:
                    s.run(client, channel)
        else:
            log.msg('not standup time in %s.' % (channel))

        reactor.callLater(60, self.check_standup_time, client, channel)

    def run_command(self, client, user, channel, command):
        log.msg('parsing command from %s: %s' % (user, command))

        command = command.split(' ', 1)
        args = ''
        if len(command) > 1:
            args = command[1]
            command = command[0]
        else:
            command = command[0]

        response = None
        for c in self.COMMANDS:
            if c.command == command:
                response = c.do_command(client, user, channel, args)

        if command == 'help':
            response = self.get_help(args)

        if response:
            client.msg(str(channel), str(response))

    def get_help(self, command):
        response = None
        if command:
            for c in self.COMMANDS:
                if c.command == command:
                    response = c.help()

        if not response:
            response = 'available commands (try "help <command>"): %s' % ', '.join(c.command for c in self.COMMANDS)

        return response
