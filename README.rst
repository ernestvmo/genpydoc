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
    include-only-covered = true
    run-on-diff = false
    run-staged = false
    target-branch = "main"
    use-llm-provider = "openai"
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
                                      the processing.  [default: False]
      -D, --run-on-diff               Only run the evaluator on Git diffed Nodes.
      -d, --run-staged                Run on staged diff changes (good for running
                                      locally before a commit).
      --target-branch TEXT            Provide the target branch for running git
                                      comparison.  [default: main]
      --use-llm-provider [openai]     Select the LLM provider.  [default: openai]
      --use-model [gpt-5-nano]        Select which LLM model to use for
                                      documenting.  [default: gpt-5-nano]
      --style [google|numpy|epytext|reST]
                                      Docstring types allowed.  [default: google]
      -h, --help                      Show this message and exit.
      -c, --config FILE               Read configuration from ``pyproject.toml``.



``include_only_covered``
^^^^^^^^^^^^^^^^^^^^^^^^

By default, the package will extract every node of a script, regardless if they already contain a docstring.
To only evaluate nodes already covered by docstrings, set this tag to ``True``, or use ``-o`` in the CLI.

``run_on_diff``
^^^^^^^^^^^^^^^

Use this flag when you want to run the tool and only cover nodes that have been diffed.
Paired up with ``run_staged`` or ``target_branch``.

``run_staged``
^^^^^^^^^^^^^^

Use this flag if you want to run the tool only local diffed changes, for example, if running with a commit hook.
The tool will use the local staged changes and compare it to the ``git`` index.

``target_branch``
^^^^^^^^^^^^^^^^^

Specify the target branch to run the ``git diff`` against. Nodes affected by the diff will be filtered and used for analysis when commenting.

``use_llm_provider``
^^^^^^^^^^^^^^^^^^^^

Specify the LLM provider to use to generate documentation. Only OPENAI is currently accepted.

``use_model``
^^^^^^^^^^^^^

Specify the LLM to use to generate documentation. As only OPENAI is currently accepted as provider, we only accept ``gpt-5-nano``.
