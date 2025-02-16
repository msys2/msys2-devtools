# msys2-devtools

Tools for MSYS2 package maintainers

Repo server commands:

* `msys2-dbssh`: Connect to the server and forward the gpg agent

CI commands:

* `msys2-srcinfo-cache`: Maintains srcinfo data for all packages in a git repo
* `msys2-pypi-cache`: Maintains a pypi metadata cache for all packages
* `msys2-sbom`: Generate a SBOM file for all packages

Installation:

For every CLI command there exists a Python package extra with the same name:

* `pip install msys2-devtools[sbom]`

In addition there exists an `all` extra that installs all dependencies.
