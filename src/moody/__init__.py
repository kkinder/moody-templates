"""
The moody templating system.

Fast and extensible. It gets the job done.

Developed by Dave Hall <dave@etianen.com>.
"""

from moody.parser import default_parser, TemplateError


compile = default_parser.compile


def render(template, **params):
    """
    Compiles and renders the given template string with the given parameters.
    
    This is just a shortcut for moody.compile(template).render(**params).
    """
    return compile(template).render(**params)
    

# TODO: alternative loader sources, such as memory.
# TODO: test memory loader
# TODO: test disk loader
# TODO: test caching and none caching loaders
# TODO: inherit from self
# TODO: set node (then use to test name expansion properly)
# TODO: import node (two types)
# TODO: render node
# TODO: decent error reporting