# ensure that any files in here don't need contrib in front of them, as the
# contrib directory is like the site-packages directory (but with known
# contents, and without handling for .pth files)
import sys

# TODO: insert more intelligently later on (before standard library, but after current directory, PYTHONPATH, etc.)
sys.path.insert(0, "contrib")
