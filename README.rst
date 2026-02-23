==========
`genpydoc`
==========

Library to automate the generation of docstrings.


What is it?
===========

The aim of the project is to employ AI to evaluate documented (and undocumented) code to establish their accuracy, and improving said documentation automatically.

Requirements
============

``genpydoc`` supports Python 3.11 and above.

Currently, we only support OpenAI models, so you must provide a valid OpenAI API key.

    export OPENAI_API_KEY=<your-key>


Installation
============

``genpydoc`` is available on `Pypi <https://pypi.org/project/genpydoc/>`_ and `GitHub <https://github.com/ernestvmo/genpydoc>`_.


Usage
=====

Run it on one of your projects:

.. code-block:: console

    genpydoc [PATH]


Configuration
=============

You can specify the following parameters, either in the ``pyproject.toml`` or through command line.


``pyproject.toml`` Configuration
--------------------------------

.. code-block::

    [tool.genpydoc]
    ignore-magic = false
    ignore-nested-classes = false
    ignore-nested-functions = false
    ignore-overloaded-functions = false
    ignore-private = false
    ignore-property-decorators = false
    ignore-setters = false
    ignore-semiprivate = false
    include-only-covered = false
    run-on-diff = false
    use-llm-provider = "llama"
    use-model = "gpt-5-nano"
    style = "google"


Command line options
--------------------

.. code-block::

    Usage: python -m genpydoc [OPTIONS] [PATHS]...

    Options:
      -m, --ignore-magic              Ignore all magic methods of classes.
                                      [default: False]

                                      NOTE: This does not include the `__init__`
                                      method. To ignore `__init__` methods, use
                                      `--ignore-init-method`.
      -C, --ignore-nested-classes     Ignore nested classes.
      -n, --ignore-nested-functions   Ignore nested functions and methods.
      -O, --ignore-overloaded-functions
                                      Ignore `@typing.overload`-decorated
                                      functions.
      -p, --ignore-private            Ignore private classes, methods, and
                                      functions starting with two underscores.
                                      [default: False]

                                      NOTE: This does not include magic methods;
                                      use `--ignore-magic` and/or `--ignore-init-
                                      method` instead.
      -P, --ignore-property-decorators
                                      Ignore methods with property
                                      setter/getter/deleter decorators.
      -S, --ignore-setters            Ignore methods with property setter
                                      decorators.
      -s, --ignore-semiprivate        Ignore semiprivate classes, methods, and
                                      functions starting with a single underscore.
      -o, --include-only-covered      Only include Node that have a docstring in
                                      the processing.
      -D, --run-on-diff               Only run the evaluator on Git diffed Nodes.
      --use-llm-provider [openai]     Select the LLM provider.  [default: openai]
      --use-model [gpt-5-nano]        Select which LLM model to use for
                                      documenting.  [default: gpt-5-nano]
      --style [google|numpy|epytext|reST]
                                      Docstring types allowed.  [default: google]
      -h, --help                      Show this message and exit.
      -c, --config FILE               Read configuration from `pyproject.toml`.
