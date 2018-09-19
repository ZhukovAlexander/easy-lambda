from .decorators import Lambda, UPDATE_EXPLICIT, UPDATE_ON_INIT, UPDATE_LAZY

from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass
