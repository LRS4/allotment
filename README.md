## Allotment  

A place to store all of the micro apps at https://shedloadofcode.com/allotment

### Creating an executable

This will use [PyInstaller](https://pyinstaller.org/en/stable/) to bundle into a single package.

```
pip install -U pyinstaller

pyinstaller --onefile program.py
```

Your bundled application should now be available in the dist folder.

## Generating a requirements.txt from a file

Since these are single page PyQt5 files we can use [pipreqs](https://github.com/bndr/pipreqs) to scan for dependencies and then create a requirements.txt file

```
pip install pipreqs

pipreqs crawlcount.py
```