"""dxf: Reading and writing real DXF files.

The only package of the product allowed to use ezdxf. It receives exact geometry from the core and never invents a number.

May import: the standard library, ezdxf, and the core packages (engine, lang, geometry, memory, shared).
May not import: any other third-party package; tools.

Not a core package: it is outside the standard-library-only rule, and
tests/test_dependency_rules.py checks that no core package imports it.

Contract stated in P0-T04; see README.md, "Repository layout".
"""
