# msys2-devtools

Tools for MSYS2 package maintainers


## Connect to the server

```bash
./msys2-dbssh
git -C msys2-autobuild/ pull
git -C msys2-devtools/ pull
git -C msys2-main-server/ pull
export GPGKEY=<signing-key-fingerprint>
```

You need a GPG agent extra socket to sign the packages and databases.


## Update services in containers

```
cd msys2-main-server
sudo docker-compose stop
sudo docker-compose up -d
```


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


## Fix pacman symlinks

```bash
echo $'mingw/x86_64 mingw64 \n mingw/i686 mingw32 \n msys/x86_64 msys \n msys/i686 msys' | while read path db; do
  for type in db files; do
    for suffix in "" .sig; do
      ( cd /srv/msys2repo/$path/ && test ! -L $db.$type$suffix && diff $db.$type{,.tar.gz}$suffix && ln -sf $db.$type{.tar.gz,}$suffix )
    done
  done
done
```


## Link latest installer

```bash
cd /srv/msys2repo/distrib/
ln -sf x86_64/$(ls x86_64/ -t | grep '.tar.xz$' | head -1) msys2-x86_64-latest.tar.xz
ln -sf x86_64/$(ls x86_64/ -t | grep '.tar.xz.sig$' | head -1) msys2-x86_64-latest.tar.xz.sig
ln -sf x86_64/$(ls x86_64/ -t | grep '.exe$' | head -1) msys2-x86_64-latest.exe
ln -sf x86_64/$(ls x86_64/ -t | grep '.exe.sig$' | head -1) msys2-x86_64-latest.exe.sig
ln -sf x86_64/$(ls x86_64/ -t | grep '.sfx.exe$' | head -1) msys2-x86_64-latest.sfx.exe
ln -sf x86_64/$(ls x86_64/ -t | grep '.sfx.exe.sig$' | head -1) msys2-x86_64-latest.sfx.exe.sig
```
