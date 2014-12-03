Gitglue
=======
It glues your repos together!


**STATUS**: I am not using or working on gitglue right now. Maybe you could try [mr](https://joeyh.name/code/mr/) instead?


What is gitglue?
----------------
Gitglue is a lightweight json-based wrapper for your git repos written in python. It allows you to execute multiple commands at once, that saves time and makes regular issues less annoying (I.e.: I want to update my vim plugins all at once and push them to my private remote!).


How do I use gitglue?
---------------------
~~Everything you can do with [gitglue is documented](https://inktrap.org/code/gitglue-your-repos-together.html).~~


What should I do now?
---------------------
*Leave feedback, find bugs, fork your own!*

Don’t forget to leave some feedback, especially about the parts you don’t like or the bugs you found. If you just want to tell me that you like gitglue that’s fine either. You are welcome to improve gitglue!


What will you do now?
---------------------
There is plenty of stuff to do:

 - implement hooks and nohooks (one usecase: try to mount the usb stick when working with the usb repo group)
 - mount, decrypt, … (because an encrypted repo would defeat the purpose, an encrypted filesystem is better, i.e. truecrypt on usb, nfs, encfs on a remote …)
 - operators (and +, not -) for -et (nice to have!)

Known bugs
----------

When your commit message is one word long (a word is something that is not seperated by a whitespace) and contains a character that must be escaped (i.e.: ') or part of a string when used in a shell, double quotes are not sufficient. You need to escape the double quotes, else they will be stripped by your shell:

`gitglue -et foo -am \"foo'bar\"` would work.

Because it is bad practice to use such characters and your commit messages should be longer anyway I won't fix this. Fixing this bug means parsing git's cli-args: That would add unnecessary complexity.
