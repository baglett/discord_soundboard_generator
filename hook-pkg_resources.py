# Runtime hook for pkg_resources
# This suppresses pkg_resources deprecation warnings and ensures compatibility

import sys
import warnings

# Suppress pkg_resources deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='pkg_resources')

# Pre-import problematic modules to ensure they're available
try:
    import jaraco.text
except ImportError:
    pass

try:
    import jaraco.functools
except ImportError:
    pass

try:
    import jaraco.context
except ImportError:
    pass

try:
    import more_itertools
except ImportError:
    pass

try:
    import platformdirs
except ImportError:
    pass
