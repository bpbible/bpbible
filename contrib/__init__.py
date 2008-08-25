# ensure that any files in here don't need contrib in front of them, as the
# contrib directory is like the site-packages directory (but with known
# contents)
import site
site.addsitedir("contrib/")
