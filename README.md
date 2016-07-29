This is a further developed verion the following project: 
https://www.droids-corp.org/blog/html/2013/04/11/diff2html_py_version_1_0_is_released.html

# diff2html

The reason why I've decided to further develop the script is that I like to see the full context of a modification. For this case the original script didn't produced a very user friendly output.

# What has been added

- On top of the page you have a drop-down list from which you can select what files you want to display in the browser
- A navigation menu has been added

# How to use it

I have create a git alias for it which automatically generates the html report and opens it in the browser

If you decide to use it the same way just edit your .gitconfig file and add the following line under the [alias] section:

    [alias]
        diff2html = "!f() { rm -rf <TEMP-DIR-LOCATION>; mkdir -p <TEMP-DIR-LOCATION>; if [ \"$1\" == \"\" ]; then echo \"No input!\" && exit; fi; git diff -U1000 $@ | python <SCRIPT-LOCATION>/diff2html.py -o <TEMP-DIR-LOCATION>/diff.html && firefox file:///<TEMP-DIR-LOCATION>/diff.html; }; f"

Just change <TEMP-DIR-LOCATION> to a temporary folder you don't need, and <SCRIPT-LOCATION> to the direcotry you store the script in

If you have added the above alias you can call as in the following example

    git diff2html HEAD HEAD^

or

    git diff2html HEAD..HEAD^

