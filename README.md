# msys2-devtools

Tools for MSYS2 package maintainers


## Connect to the server

```sh
./msys2-dbssh
git -C msys2-autobuild/ pull
git -C msys2-devtools/ pull
git -C msys2-main-server/ pull
export GPGKEY=<signing-key-fingerprint>
```

You need a GPG agent extra socket to sign the packages and databases.


## Update services in containers

```sh
sudo docker-compose up -d --build --project-directory msys2-main-server
```


## Update databases from CI

The queue can be seen at https://packages.msys2.org/queue, the artifacts at https://github.com/msys2/msys2-autobuild/releases.

Add new packages:

```sh
python3 msys2-autobuild/autobuild.py fetch-assets staging/
msys2-devtools/msys2-dbadd
```

Remove old packages:

```sh
msys2-devtools/msys2-dbremove msys foo-git
msys2-devtools/msys2-dbremove mingw32 mingw-w64-i686-foo-git
msys2-devtools/msys2-dbremove mingw64 mingw-w64-x86_64-foo-git
```

Sync to SourceForge:

```sh
msys2-devtools/msys2-dbsync SF_USERNAME
```


## Fix pacman symlinks

```sh
echo $'mingw/x86_64 mingw64 \n mingw/i686 mingw32 \n msys/x86_64 msys \n msys/i686 msys' | while read path db; do
  for type in db files; do
    for suffix in "" .sig; do
      ( cd /srv/msys2repo/$path/ && test ! -L $db.$type$suffix && diff $db.$type{,.tar.gz}$suffix && ln -sf $db.$type{.tar.gz,}$suffix )
    done
  done
done
```


## Update installer

```sh
./update-installer 2021-02-28
```
