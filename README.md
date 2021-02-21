# msys2-devtools

Tools for MSYS2 package maintainers


## Connect to the server

```bash
./msys2-dbssh
git -C msys2-autobuild/ pull
git -C msys2-devtools/ pull
git -C msys2-repo-server/ pull
```

You need a GPG agent extra socket to sign the packages and databases.


## Update databases from CI

The queue can be seen at https://packages.msys2.org/queue, the artifacts at https://github.com/msys2/msys2-autobuild/releases.

Add new packages:

```bash
python3 msys2-autobuild/autobuild.py fetch-assets staging/
msys2-devtools/msys2-dbadd
```

Remove old packages:

```bash
msys2-devtools/msys2-dbremove msys foo-git
msys2-devtools/msys2-dbremove mingw32 mingw-w64-i686-foo-git
msys2-devtools/msys2-dbremove mingw64 mingw-w64-x86_64-foo-git
```

Sync to SourceForge:

```bash
msys2-devtools/msys2-dbsync SF_USERNAME
```
