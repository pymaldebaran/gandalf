# Gandalf - A Telegram event planner bot #

Gandalf is a [Telegram bot](https://telegram.org/blog/bot-revolution) that helps you organise your plannings. It's quite similar to [@vote bot](https://telegram.me/vote) in terms of functionnality except Gandalf provides a live list of "who voted for what". You can see it as an "open vote system" or "hand vote" since vote are not secret but the initial objective of Gandalf is to provide a simple way to organise events/planings.

You know those moments when you want to know who is available at what moments. It can be used in différent sotuations:

> When do you prefer to have this party folks?
> * Monday at 6pm afterwork-style?
> * Monday at 8pm since everybody is always late?
> * Thursday at 8pm (not in my place but Mike's appartment looks like a great place to ruin)?
> * Saturday at 11pm for a real party?

Your friends will simply vote for their favorite(s) day(s) and you can then see who is available and when. In this case Gandalf can be used as an equivalent to (Doodle)[http://doodle.com]: when you close the planning you can choose the perfect moment to do your awesome party.

> When could you be there to help us move in to our new appartment Friday?
> * 8am to 9am --> loading and driving
> * 9am to 10am --> unloading and maybe some driving
> * 10am to 11am --> unloading and mainly moving things up the stairs (muscle time, it's 5th floor!)
> * 11am to noon --> mainly unpacking
> * Afternoon (whatever the hour) --> unpacking and couch testing!

You can also use Gandalf to know who will be available when (or where Gandalf is not necessarly time related). As Gandalf gives you the exact list of who votes for what option.

<!-- TODO add some screenshots here -->

<!-- ## Recent changes ## -->

## Getting Started ##

### Prerequisities ###

* This python bot is developped for [python 3](https://www.python.org/download/releases/3.0/). You have to install it for your platform (having python 2.x and python 3 is possible).
* To launch the bot you need to get a [Telegram Bot API TOKEN](https://core.telegram.org/bots#3-how-do-i-create-a-bot).

### Running the program ###

First you need to create a database for your server:

```shell
$ ./gandalf.py createdb
Database file <plannings.db> already existed and was deleted.
New database file <plannings.db> created.
```

Then you just need to launch the program in server mode but you need to provide it a valid [Telegram Bot API token](https://core.telegram.org/bots#3-how-do-i-create-a-bot) (here I use a dummy one):

```shell
$ ./gandalf.py serve 123456789:uLJLzM7FG7Fc3dW1qY6FUVmbzw378xUWH74
My name is Name_of_your_bot and you can contact me via @username_of_you_bot and talk to me.
Listening ...
```

From that moment on you can communicate via any Telegram client with your bot !

For an always up-to-date documentation on usage, Gandalf is a command line tool with extensive usage documentation:

```shell
$ ./gandalf.py --help
usage: gandalf.py [-h] {serve,createdb,autotest} ...

positional arguments:
  {serve,createdb,autotest}
    serve               listen for chats
    createdb            create new database file
    autotest            launch all unittests for Gandalf.

optional arguments:
  -h, --help            show this help message and exit
```

### Installing ###

To install dependancies simply use `pip3` and the provided `requirements.txt`:

```shell
pip3 install -r requirements.txt
```

## Running the tests ##

Running the test is integrated directly in the `gandalf.py` file using the `autotest` command:

```shell
$ ./gandalf.py autotest
```

It will run all tests:

* Doctests included in the code
* unittests specific to each class, function or more generic functionnality
* functional tests that simulate some real life usage of the bot

## For developers ##

* Please conform to the [https://www.python.org/dev/peps/pep-0008/](PEP 8) style guide and [PEP 257](http://www.python.org/dev/peps/pep-0257/). If you're using SublimeText editor you can be checked easily with the plugin [SublimeLinter](http://www.sublimelinter.com/en/latest/) and its 2 companions [SublimeLinter-pep8](https://github.com/SublimeLinter/SublimeLinter-pep8) and [SublimeLinter-pydocstyle](https://github.com/SublimeLinter/SublimeLinter-pydocstyle).
* [git-flow](http://danielkummer.github.io/git-flow-cheatsheet/) is recommended (but not enforced) as a development work flow. For instruction please read [Why aren't you using git-flow?](http://jeffkreeftmeijer.com/2010/why-arent-you-using-git-flow/). To adapt it, a command line tool gitflow is highly recommended.
* Please work on the develop branch, it's newer than master. the master branch is for release version destinated to the final users.


## Authors ##

* **Pierre-Yves "PYM" MARTIN** - *Initial work* - [pymaldebaran](https://github.com/pymaldebaran)

## License ##

This project is licensed under the AGPL v3.0 License - see the [gnu-agpl-v3.0.md
](gnu-agpl-v3.0.md
) file for details.

## Acknowledgments ##

* [Nick Lee](https://github.com/nickoala) for it's wonderful [Telepot](https://github.com/nickoala/telepot) - _Python framework for Telegram Bot API_ and it's incredible response time when I had some problems.
* [@vote bot](https://telegram.me/vote) and [@like bot](https://telegram.me/like) which were great inspiration for my UI and interaction model.
* [My capoeira team](http://www.lacademia.fr) in Paris for which I developed this whole program in order to simplify our everyday life.
* [IQAndreas](https://github.com/IQAndreas) for his [markdown formated version of the common open source licenses](https://github.com/IQAndreas/markdown-licenses)
* [PurpleBooth README-Template.md](https://gist.github.com/PurpleBooth/109311bb0361f32d87a2) that I used for this very README.

