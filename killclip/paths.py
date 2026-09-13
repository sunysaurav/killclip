"""Where configs, templates and logs live. Running from a source checkout: the checkout. Installed as a
package: $KILLCLIP_HOME if set, else ~/.killclip (holds configs/, calib/, logs/)."""
import os

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.environ.get("KILLCLIP_HOME") or (_SRC if os.path.isdir(os.path.join(_SRC, "configs")) else os.path.expanduser("~/.killclip"))
