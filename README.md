### Build

```bash
docker-compose build
```

### Run

```bash
WS_CONNECTION='wss://this.piston.rocks' docker-compose up
```

### Use

Tarantool database should be available on port 3301 of your local host.

To access the data via console please to the following:

```bash
$ docker-compose exec datastore /bin/sh
$ tarantoolctl connect guest@localhost:3301
```

