# Content Repository

This content repository allows easy content management via a headless CMS, using [wagtail](https://wagtail.io/) that is meant for web and various messaging platforms.

## Releases
[Semantic versioning](https://semver.org/) is in use in this project.
1. Feature releases
    - Feature releases are a MAJOR.MINOR combination, eg. `1.2`
    - Feature releases occur once every 3 months, but only if required. eg. If there were only patch releases in the last 3 months, no feature release will occur.
    - The latest feature release will receive any security or bug fixes as patch releases
    - Each feature release will have a separate git branch
1. Patch releases
    - Patch releases are used to fix bugs and security issues
    - They are released as soon as they are ready
1. LTS (Long-Term Support) Releases
    - Every fourth release is an LTS release
    - LTS releases are listed in the documentation
    - LTS releases receive security patches
    - LTS releases are supported for 5 feature releases, allowing for 15 months of support with a 3 month switchover time to the next LTS
1. Development releases
    - Development have the `-dev.N` suffix
    - They are used to test new code before an official release is made
    - They are built off of the `main` git branch

## Setting up locally

### Redis

For Linux and WSL2 (Windows Subsystem for Linux)
 Creating a docker container with the ports exposed, called `cr_redis`
`docker run -d -p 6379:6379 --name cr_redis redis`

To then run the docker container,
`docker run cr_redis`

This can work for mac and (possibly Windows) by setting the environment variable `DATABASE_URL=postgres://postgres@0.0.0.0/contentrepo`

### Postgres

For Linux and WSL2 (Windows Subsystem for Linux)
Creating a docker container that doesnt require a password and matches the setup of the database in settings
`docker run --name cr_postgres -p 5432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=postgres -e POSTGRES_DB=contentrepo -d postgres:latest`

To then run the docker container,
`docker run cr_postgres`

This can work for mac and (possibly Windows) by setting the environment variable `DATABASE_URL=postgres://postgres@0.0.0.0/contentrepo`

### Wagtail server

Run the following in a virtual environment
```bash
pip install -r requirements.txt
pip intsall -r requirements-dev.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
