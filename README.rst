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


Command line options
--------------------

.. option:: -m, --ignore-magic

    Ignore all magic methods of classes.
    [default: False]

    NOTE: This does not include the `__init__`
    method. To ignore `__init__` methods, use
    `--ignore-init-method`.

.. option:: -C, --ignore-nested-classes

    Ignore nested classes.

.. option:: -n, --ignore-nested-functions

    Ignore nested functions and methods.

.. option:: -O, --ignore-overloaded-functions

    Ignore `@typing.overload`-decorated functions.

.. option:: -p, --ignore-private

    Ignore private classes, methods, and functions starting with two underscores. [default: False]

    NOTE: This does not include magic methods;
    use `--ignore-magic` and/or `--ignore-init-
    method` instead.

.. option:: -P, --ignore-property-decorators

    Ignore methods with property setter/getter/deleter decorators.

.. option:: -S, --ignore-setters

    Ignore methods with property setter decorators.

.. option:: -s, --ignore-semiprivate

    Ignore semiprivate classes, methods, and functions starting with a single underscore.

.. option:: -o, --include_only_covered

    Only include Node that have a docstring in the processing.

.. option:: -D, --run_on_diff

    Only run the evaluator on Git diffed Nodes.

.. option:: --use_llm_provider [openai]


    [default: openai]

.. option:: --use_model [gpt-5-nano]

    [default: gpt-5-nano]

.. option:: --style [google|numpy|epytext|reST]

    [default: google]

.. option:: -h, --help

    Show this message and exit.

.. option:: -c, --config FILE

    Read configuration from `pyproject.toml`.
