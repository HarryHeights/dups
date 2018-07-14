import datetime
import logging
import os
import socket
import traceback
from contextlib import contextmanager
from typing import Tuple

import dbus
import paramiko
import ruamel.yaml

from . import backup, config, const, exceptions, rsync, user, utils

LOGGER = logging.getLogger(__name__)


def configure_logger():
    """Configure the logger based on the config file."""
    cfg = config.Config.get()
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    for name, level in cfg.logging.items():
        logging.getLogger(name).setLevel(level)


def prepare_env(username):
    usr = user.User.get()
    usr.set_user(username)

    os.environ['USER'] = usr.user
    os.environ['HOME'] = usr.home
    os.environ['XDG_RUNTIME_DIR'] = usr.xdg_runtime_dir


def prepare_config(config_file=None):
    try:
        if config_file:
            config_file = os.path.abspath(config_file)
        else:
            usr = user.User.get()
            config_file = usr.config_file

        cfg = config.Config.get()
        cfg.config_file = config_file
        cfg.reload()

    except FileNotFoundError:
        print('The config file "{}" does not exist.'.format(cfg.config_file))
        return None

    except ruamel.yaml.parser.ParserError:
        print('Invalid config at "{}". Check for any syntax errors.'.format(
            cfg.config_file))
        return None

    return cfg


def configure_rsync():
    """Configure rsync based on the config file."""
    cfg = config.Config.get()
    sync = rsync.rsync.get()

    sync.rsync_bin = cfg.rsync['rsync_bin']
    sync.ssh_bin = cfg.rsync['ssh_bin']

    sync.ssh_config_file = cfg.target['ssh_config_file']
    sync.ssh_key_file = cfg.target['ssh_key_file']
    sync.ssh_known_hosts_file = cfg.target['ssh_known_hosts_file']

    sync.acls = cfg.rsync['acls']
    sync.xattrs = cfg.rsync['xattrs']
    sync.prune_empty_dirs = cfg.rsync['prune_empty_dirs']
    sync.out_format = cfg.rsync['out_format']


def get_configured_io():
    """Get a `io.IO`_ instance based on the users configuration.
       Better use `configured_io`_ to automatically close sessions.

    Returns:
        io.IO: A instance of `io.IO`_.
    """
    cfg = config.Config.get()

    t = cfg.target
    return utils.IO.get(t['host'], t['port'], t['username'],
                        t['ssh_config_file'], t['ssh_key_file'],
                        t['ssh_known_hosts_file'])


@contextmanager
def configured_io():
    """Contextmanager wrapper for `get_configured_io`_.

    Yields:
        io.IO: A instance of `io.IO`_.

    Example:
        >>> with configured_io() as io:
                pass
    """
    io = None
    try:
        io = get_configured_io()
        yield io

    finally:
        if io:
            io.close()


def error_handler(callback, *args, **kwargs):
    """Handle the given callback and catch all exceptions if some should
       arise.

    Args:
        callback (function): The function to execute.
        *args: Arguments to pass to the callback.
        **kargs: Keyword-Arguments to pass to the callback.
    """
    error_msg = None
    try:
        res = callback(*args, **kwargs)
        return (True, res)

    except paramiko.ssh_exception.BadHostKeyException:
        error_msg = 'Host key verification failed.'

    except paramiko.ssh_exception.SSHException as e:
        LOGGER.debug(traceback.format_exc())
        error_msg = str(e)

    except paramiko.ssh_exception.NoValidConnectionsError as e:
        LOGGER.debug(traceback.format_exc())
        error_msg = str(e)

    except (KeyError, socket.gaierror):
        error_msg = 'Could not connect to host.'

    except dbus.exceptions.DBusException:
        LOGGER.debug(traceback.format_exc())
        error_msg = 'Unable to connect to daemon. Is one running?'

    except (exceptions.BackupAlreadyExistsException,
            exceptions.BackupNotFoundException) as e:
        error_msg = str(e)

    except KeyboardInterrupt:
        error_msg = 'Process canceled.'

    except Exception as e:
        LOGGER.debug(traceback.format_exc())
        error_msg = 'Something bad happend. Try increasing the log-level.'
        error_msg += str(e)

    return (False, error_msg)


def notify(title, body=None, priority=None, icon=const.APP_ICON):
    """Send a new notification to a notification daemon unless configured
       otherwise by the user.

    Args:
        title (str): The notifications title.
        body (str): The notifications body.
        priority (utils.NPriority): The notifications priority level.
        icon (str): Name or path of the notifications icon.
    """
    cfg = config.Config.get()

    if not cfg.notify:
        return

    app_id = const.DBUS_NAME + '.notification'
    utils.notify(app_id, title, body, priority, icon)


def get_backups(include_valid=True, include_invalid=True):
    """Get a sorted list of all available backups.

    Returns:
        list: A sorted list of `backup.Backup`_ for the users configured
            target.
    """
    cfg = config.Config.get()

    with configured_io() as io:
        backups = sorted(
            backup.Backup.all_backups(io, cfg.target['path'], include_valid,
                                      include_invalid))
        return backups


def print_backups():
    """Print a list of all available backups in a pretty way."""
    backups = get_backups()

    print('Name', '\t\t', 'Date', '\t\t\t', 'Valid')
    for b in backups:
        valid = 'yes' if b.is_valid else 'no'
        print(b.name, '\t', b.name_pretty, '\t', valid)


def create_backup(dry_run=False,
                  client=None) -> Tuple[backup.Backup, rsync.Status]:
    """Creates a new backup based on the users configuration.

    Args:
        dry_run (bool): Whether or not to perform a trial run with no
            changes made.
        background (bool): Whether or not to instruct a daemon instance to
            perform the backup.

    Returns:
        tuple: (`backup.Backup`_, `rsync.Status`_) if `background`_ was set to
            `False`, (`None`, `None`) otherwise.
    """
    cfg = config.Config.get()

    if client:
        client.backup(dry_run)
        return None, None
    else:
        utils.add_logging_handler('backup.log')

        with configured_io() as io:
            bak = backup.Backup.new(io, cfg.target['path'])
            status = bak.backup(
                cfg.get_includes(True), cfg.get_excludes(True), dry_run)

            return bak, status


def restore_backup(items=None, name=None, target=None, dry_run=False,
                   client=None):
    """Starts a new restore based on the users configuration.

    Args:
        items (list): List of files and folders to be restored.
            If `None` or empty, the entire backup will be restored.
        name (str): The name of the backup to restore from.
            If `None`, the most recent backup will be used.
        target (str): Path to where to restore the backup to.
            If `None` or "/", all files will be restored to their original
            location.
        dry_run (bool): Whether or not to perform a trial run with no
            changes made.
        background (bool): Whether or not to instruct a daemon instance to
            perform the restore.

    """
    cfg = config.Config.get()

    if client:
        name = '' if not name else name
        client.restore(items, name, target, dry_run)
        return None, None
    else:
        with configured_io() as io:
            if name:
                bak = backup.Backup.from_name(io, name, cfg.target['path'])
            else:
                bak = backup.Backup.latest(io, cfg.target['path'])

            if not bak:
                raise exceptions.BackupNotFoundException(
                    'No backup to restore from!')

            if target:
                target = os.path.abspath(target)

            utils.add_logging_handler('restore.log')

            status = bak.restore(target, items, dry_run)
            return bak, status


def remove_backups(names, dry_run=False):
    """Remove the given backups based on the users configuration.

    Args:
        names (list): List of Names of backups to remove.
        dry_run (bool): Whether or not to perform a trial run with no
            changes made.
    """
    cfg = config.Config.get()

    with configured_io() as io:
        for name in names:
            try:
                b = backup.Backup.from_name(io, name, cfg.target['path'])
            except exceptions.BackupNotFoundException:
                print('Backup "{}" does not exist!'.format(name))
                continue

            if not dry_run:
                b.remove()

            print('Successfully removed "{}"'.format(name))


def remove_but_keep(keep, dry_run=False):
    """Remove all but keep `keep` amount of the most recent backups.

    Args:
        keep (int): Amount of most recent backups to keep.
        dry_run (bool): Whether or not to perform a trial run with no
            changes made.
    """
    if keep == 0:
        names = list(b.name for b in get_backups())
    else:
        names = list(b.name for b in get_backups()[:-keep])

    remove_backups(names, dry_run)


def remove_older_than(duration, dry_run=False):
    """Remove all backups older than the given `duration`.

    Args:
        duration (str): Remove backups older than this.
            See `utils.duration_to_timedelta`_ for the format.
        dry_run (bool): Whether or not to perform a trial run with no
            changes made.
    """
    try:
        older_than = (
            datetime.datetime.now() - utils.duration_to_timedelta(duration))
    except ValueError:
        print('Invalid duration specified.')
        return

    names = []
    for b in get_backups():
        if b.datetime > older_than:
            break
        names.append(b.name)

    remove_backups(names, dry_run)
