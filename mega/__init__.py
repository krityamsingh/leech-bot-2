import os
import sys
import importlib

# Import base Mega from mega.py (site-packages) bypassing this local folder
orig_path = list(sys.path)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if p and os.path.abspath(p) != parent_dir]
orig_mega = sys.modules.pop('mega', None)

USING_REAL_SDK = False

try:
    real_mega = importlib.import_module('mega.mega')
    if hasattr(real_mega, "MegaApi"):
        # The site-packages mega is the actual compiled C++ SDK bindings!
        # Redirect sys.modules['mega'] to real_mega.
        sys.modules['mega'] = real_mega
        # Also copy all its attributes to the current module's namespace
        globals().update({k: getattr(real_mega, k) for k in dir(real_mega) if not k.startswith('_')})
        USING_REAL_SDK = True
except Exception:
    pass
finally:
    sys.path = orig_path
    if orig_mega and not USING_REAL_SDK:
        sys.modules['mega'] = orig_mega

if not USING_REAL_SDK:
    # Load the emulation/shim class from the local emulation file
    from .emulation import *
