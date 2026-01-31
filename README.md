# TVA meta

Repository aggregating TVA activity, for internal management and reportting to ESDIS.

It works together with the TVA project, but here, in the repository are specifically hosted:
- Issues which overlap multiple repositories
- GitHub actions to propagate changes across repositories and projects

A set of github action helps with the synchronization across repository and reporting:
- Automatically synchronize the projects attributes from Hitide and SOTO to thi TVA project.
- Automatically propagate the ESDIS reference in TVA tickets to child issues.
- Manually synchronize iteration across projects
- Manually synchronize labels across repositories
- 

## Test a github action locally

Use `act` to test github actions locally. For example:

    act -j propagate --container-architecture linux/amd64 -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-latest


Then attach the debugger to the act service, if needed.


