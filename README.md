# TVA meta

project aggregating TVA activity, for internal management and reportting to ESDIS.

A set of github action helps with the synchonization across repository and reporting

## Test a github action locally

Use `act` to test github actions locally. For example:

    act -j propagate --container-architecture linux/amd64 -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-latest


Then attach the debugger to the act service, if needed.


