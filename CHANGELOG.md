# Changelog

## [8.0.0](https://github.com/Garulf/twitchy/compare/v7.0.0...v8.0.0) (2026-11-17)


### ⚠ BREAKING CHANGES

* the plugin now runs on Flow Launcher's python_v2 runtime and needs Python 3.10 or newer.

### Features

* port to pyflowlauncher on the python_v2 runtime ([f931bb7](https://github.com/Garulf/twitchy/commit/f931bb76cb2f506eeabfed167d17aad1097e7eb8))


### Bug Fixes

* fall back to the stream URL when program arguments are blank ([2ce2e1c](https://github.com/Garulf/twitchy/commit/2ce2e1c2f1d7b7c604cf982507816aadf28e8cc6))
* look up users and streams in batches of 100 ids ([5384aa5](https://github.com/Garulf/twitchy/commit/5384aa5f91c6294252915aa44f94b4a27036ebe8))
* skip the program entry when a channel has no live stream ([e465de1](https://github.com/Garulf/twitchy/commit/e465de13b15c45916b086706a505637bba348e64))
