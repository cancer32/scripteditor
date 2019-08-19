# scripteditor
An external python script editor for Autodesk Maya. With the help of it we can connect to the maya's commandPort openned on the host.

# Requirements
* Python 2.7 or 3.X
* PyQt4 or PyQt5

# How to use
1. First open a commandport on the maya by running the below python command.

#    import maya.cmds as cmds
#    host = '127.0.0.1'    # For connecting from remote host use the IP address of the machine
#    port = 5050
#    if not cmds.commandPort('%s:%s' %(host,port), q=True):
#        cmds.commandPort(n='%s:%s' %(host,port), stp='python')
        
2. Run the scripteditor.py.
3. Click Connect button and give Host & Port given on step 1.
4. Run the selected command or whole script.







<div>Icons made by <a href="https://www.flaticon.com/authors/smashicons" title="Smashicons">Smashicons</a> from <a href="https://www.flaticon.com/"         title="Flaticon">www.flaticon.com</a> is licensed by <a href="http://creativecommons.org/licenses/by/3.0/"         title="Creative Commons BY 3.0" target="_blank">CC 3.0 BY</a></div>
