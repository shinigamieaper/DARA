# Re-export seed.py symbols so that `import seed` works whether Python
# resolves this package or the seed.py module directly (pytest path quirk).
try:
    from seed.seed import *  # noqa: F401, F403
    from seed.seed import build_parser, main, DATASETS  # noqa: F401
except ImportError:
    pass
