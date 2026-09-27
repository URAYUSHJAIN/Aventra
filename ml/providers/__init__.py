"""Provider layer: interface, capability matrix, registry, router, rate limiting and health.

The ML pipeline never imports a concrete provider; it asks the router for normalised series.
"""
