# QKeysOnScreen

[Demo video](https://www.youtube.com/watch?v=oOToCqTvW6U&feature=youtu.be)

- [![Video preview](https://i.ytimg.com/vi/oOToCqTvW6U/hqdefault.jpg)](https://www.youtube.com/watch?v=oOToCqTvW6U&feature=youtu.be)

## Synopsis

QKeysOnScreen shows the current keys you're pressing on the screen. It is
QiPress / Keypose / KeyCastr for GNU/Linux.

It uses PyQt5 for the GUI and evdev to read your keys, making it much better
than `key-mon`. See "Comparison with key-mon" below.

QKeysOnScreen was inspired by the widget in the top right of the screen in
TempleOS. I had never written a non-trivial Qt application before, and needed
to make an ED25519 key manager. I started writing this to learn Qt, but by the
time I was finished it was a full featured application.

## Usage

QKeysOnScreen is completely GUI driven and has no command line options. You can
configure it by right clicking the main window to see a list of options.
QKeysOnScreen is very configurable, just about every aspect of it can be
configured. You can change the font, color, window size, divider, ignored keys,
and fadeout behavior. If you can think of more useful options, please open a
GitHub issue.

## Dependencies

* Qt 5 (tested only on Qt 5.5.0)
* PyQt5
* Python 3
* [python-evdev](https://python-evdev.readthedocs.org/en/latest/)

## Troubleshooting

QKeysOnScreen uses the Linux kernel's `evdev` interface. This makes it very
fast and accurate, but also makes setup a bit tricky.

Owing to the Linux kernel's security, it does not just allow any unprivileged
user to capture keyboard events. This is a good thing™, because in its essence
QKeysOnScreen is a keylogger, except it doesn't save or send the keys anywhere,
it just displays them on the screen.

There are three ways to give QKeysOnScreen the permissions it needs:

* Run it with `sudo`. This is by far the simplest and most secure way, as it
  only gives permission to QKeysOnScreen and no other applications. However, it
may not be ideal if you want your Qt widget styling to carry over, or if you
want to run it from the desktop menu.

* Add yourself to the group that the input devices are in, so your user can
  read them. This group is usually called `input` or `plugdev`, but you can
check for sure by doing `ls -l /dev/input/event0`. The word after `root` is the
input group. Then do `sudo gpasswd -a your_username input_group_here`. Then,
log out and log in, and QKeysOnScreen should now start under your user.

* Add a udev rule. I don't know how (and believe me, I tried _really_ hard), so
  please open a GitHub issue if you find out how so I can write how here.

## Comparison with `key-mon`

1. key-mon uses GTK, and that's just for heretics.
2. key-mon does not persist keys properly. It has a key timeout, but it has no
   way to show keys until the next one is pressed.
3. key-mon is unmaintained, and is hosted on Google Code. RIP
4. key-mon has no key history window.
5. key-mon is buggy. For example, key-mon does not understand Ctrl-C if the
   Preferences window is open, and can only be killed by `kill -9`. key-mon's
"Highly Visible Click" functionality, while there (I'll add it to QKOS soon),
is incredibly buggy. Sometimes the circle around clicks persists for _minutes_
longer than it should.
6. key-mon is bound to X11 in an unhealthy way. key-mon uses the X11 RECORD
   extension, which means it doesn't work with Wayland. QKeysOnScreen uses
evdev. If you open a tty on one monitor, QKeysOnScreen will continue to work
with the keys you are pressing in that tty, and [QKeysOnScreen works perfectly
with Wayland.](http://web.archive.org/web/20190326095102if_/https://track3.mixtape.moe/bttmbn.png)

![QKeysOnScreen in Wayland! :)](http://web.archive.org/web/20190326095102if_/https://track3.mixtape.moe/bttmbn.png)
