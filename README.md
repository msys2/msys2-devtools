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
# Pull new base images and re-build things
sudo docker-compose -f msys2-main-server/docker-compose.yml --project-directory msys2-main-server build --pull
# Restart changed services
sudo docker-compose -f msys2-main-server/docker-compose.yml --project-directory msys2-main-server up -d
# Clean up old things (optional)
sudo docker system prune --all --force
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
msys2-devtools/msys2-dbremove-api
```

Sync to SourceForge:

```sh
msys2-devtools/msys2-dbsync SF_USERNAME
```


## Update installer

```sh
msys2-devtools/update-installer 2021-02-28
```
