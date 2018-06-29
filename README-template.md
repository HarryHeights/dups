dups
====
[![Say Thanks!](https://img.shields.io/badge/say-thanks-e91e63.svg)](https://saythanks.io/to/tadly)
[![Build Status](https://travis-ci.org/linuxwhatelse/dups.svg?branch=master)](https://travis-ci.org/linuxwhatelse/dups)

**Even though I actively use `dups` already, it should still be considered alpha!**

It deduplicates things - Backup as simple as possible.

As there was no linux backup solution that was simple and
_to the point_-enough to fit my needs, I decided to write my own.

`dups` is powered by `rsync` using the amazing `--link-dest` option to
save space **and** time when backing up.

What this does is it creates [hard links](https://en.wikipedia.org/wiki/Hard_link) to **unchanged** files from the
previous backup meaning they don't have to be transfered again **and** do not
take up additional disk space.

Another priority of mine was the ability to acces backups without any special
software.
As each backup is just a _dumb_ replication of your local content, this is
easily achieved.


## Requirements
### System dependencies
```
[[ req-sys ]]
```

### Python dependencies
```
[[ req-py ]]
```


## Todo
- [ ] Unit tests
- [ ] Remove old backups based on the [GFS](https://en.wikipedia.org/wiki/Backup_rotation_scheme#Grandfather-father-son) rotation scheme
- [ ] Logo/App icon preferably fitting the [Paper Icon Theme](https://snwh.org/paper) (help wanted)


## Installation
### archlinux
There's a package in the aur: [dups-git](https://aur.archlinux.org/packages/dups-git/)

### Other
```sh
pip install git+https://github.com/linuxwhatelse/dups
```


## Configuration
`dups` reads its config from `~/.config/dups.yaml` (create it if it doesn't
exist) and combines it with some default values which you can find [here](dups/data/config.yaml).

Hence a basic user config would look something like this:
```yaml
target:
  path: '/absolute/path/to/remote/backup/directory'
  host: 'backup-server-hostname'
  username: 'root'
```


## Gotchas
### User/Group for files and folders are not properly backed up.
On unix systems it is typical that **only** root can change a files/folders
user and group.
To keep the user and group, you'd have to connect with root to the remote system.


## Usage
For the time being, here's the help text.
```text
[[ help ]]
```
