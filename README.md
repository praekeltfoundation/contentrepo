# Content Repository

This content repository allows easy content management via a headless CMS, using [wagtail](https://wagtail.io/) that is meant for web and various messaging platforms.

## Features

- **Multi-channel support:** Currently supports Web, WhatsApp,Messenger,Viber, SMS and USSD.
- **Ordered content sets:** You can take individual pieces of content and group them in a set, in a specific order. They can also be restricted to users with specific profile field values.
- **Stage based messaging:** Ordered content sets can be expanded to include a relative time (eg. 23 days before x), to create a timing-based push-message journey.
- **Import and export:** Content and ordered content sets can be exported and imported in CSV and Excel formats
- **Page views:** Content page views for each channel can be stored, with reporting in the admin UI. Custom fields for each page view can also be stored (eg. user ID)
- **Rich media support:** Can store images for Messenger and Viber, and images, documents, audio and video for WhatsApp.
- **Custom branding:** Can configure the title, login and welcome messages, logo, and favicon for the content admin UI
- **Variation messaging:** Support for variations on WhatsApp messages for different user profiles fields: age, gender, and relationship status.
- **Content tree:** Content is stored in a tree format, allowing arbitrary-depth nested menu structures
- **Tags:** Content can be tagged to group certain kinds of content together
- **Triggers:** Triggers can be added to content, to specify custom triggers for when a piece of content should be sent
- **Quick replies:** A list of quick replies/buttons can be added to the content
- **Related pages:** Each piece of content can be linked to other content pages that are related to it, that can be suggested to users.
- **WhatsApp templates:** WhatsApp template messages can be stored, with the option of also submitting them to the WhatsApp Business API for approval
- **Page ratings:** Content pages can be rated by the user as helpful or not helpful, with text comments.
- **API authentication:** The API requires authentication to access. This can be through an authentication token, basic authentication, or session cookie.
- **Suggested content:** Return a random sample of child pages from a supplied list of parent pages.
- **Search:** Find content pages through a search query.
- **Internationalisation:** Content can be translated into different locales.
- **Reports:** Reports on page views, to see how well a content page is doing, and stale content, to see which content needs to be updated.
- **Workflow management:** Can create or modify content in a draft state; comment, collaborate, and refine it; and define a workflow for how the changes can make their way into being published.


## Releases
[Semantic versioning](https://semver.org/) is in use in this project.

1. Development releases
    - Development versions have the `-dev.N` suffix
    - They are built off of the `main` git branch
    - They are created with git tags, eg. `v1.2.0-dev.2`
    - Development releases are created before releases, eg. `v1.2.0-dev.0` gets created before `v1.2.0`
1. Releases
    - Releases have a semantic version number, eg. `1.2.0`
    - Releases are created when the changes have passed QA
    - They are built off of the `main` git branch
    - They are created with git tags, eg. `v1.2.0`

### How to create a release

1. Check that `CHANGELOG.md` is up to date.
1. Update the version number in `pyproject.toml` to the version you want to release, eg. change `1.2.0-dev.0` to `1.2.0`
1. Either create a pull request with these changes, and have it reviewed, or post a diff in Slack and have it reviewed there. Then merge, or commit and push, the changes.
1. Tag these changes with the desired release, eg. `git tag v1.2.0`, and push the tag, eg. `git push --tags`
1. Update the version number in `pyproject.toml` to the next version number, eg. `1.2.1-dev.0`.
1. Commit and push that change.


## Setting up locally

### Redis

For development environments, Redis is optional, it will use an in-memory cache by
default if the environment variable isn't specified.

For Linux and WSL2 (Windows Subsystem for Linux)
 Creating a docker container with the ports exposed, called `cr_redis`
`docker run -d -p 6379:6379 --name cr_redis redis`

To then start the docker container,
`docker start cr_redis`

This can work for mac and (possibly Windows) by setting the environment variable `CACHE_URL=redis://0.0.0.0:6379/0`

### Postgres

Local tests run using in-memory sqlite, so postgres isn't required.

For Linux and WSL2 (Windows Subsystem for Linux)
Creating a docker container that doesn't require a password and matches the setup of the database in settings
`docker run --name cr_postgres -p 5432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=postgres -e POSTGRES_DB=contentrepo -d postgres:latest`

To then start the docker container,
`docker start cr_postgres`

This can work for mac and (possibly Windows) by setting the environment variable `DATABASE_URL=postgres://postgres@0.0.0.0/contentrepo`

Then create the DB by entering the cr_postgres container and creating a db, note that the user will need to be changed from root to postgres
```bash
docker exec -it cr_postgres bash  
su - postgres
createdb contentrepo
```

### Wagtail server

Run the following in a virtual environment
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

### Automated tests

Tests are run using [pytest](https://pytest.org). For faster test runs, try adding `--no-cov` to disable coverage reporting and/or `-n auto` to run multiple tests in parallel.

## API
The API documentation is available at the `/api/schema/swagger-ui/` endpoint.

### Authentication
Authentication is required to access the API. Session, basic, and token authentication is supported, but token authentication is advised.

To create an authentication token, you can do so via the Django Admin (available at the `/django-admin` endpoint), or by `POST`ing the username and password of the user you want to generate a token for to the `/api/v2/token/` endpoint.

### Internationalisation
To create or import pages in other languages, the user must first create the locale and HomePage in the specified language. To create a new locale, go to "Settings" => "Locales" in the admin interface, and click "Add a new locale". Then go to the default(most likely English) homepage, click the kebab menu and select translate. This will copy the whole default tree into the new locale, creating the new homepage with all the required pages. After you press "Save", there should be two "Home" pages in the page explorer. 

## Running in Production
There is a [docker image](https://github.com/praekeltfoundation/contentrepo/pkgs/container/contentrepo) that can be used to easily run this service. It uses the following environment variables for configuration:

| Variable      | Description |
| ----------    | ----------- |
| SECRET_KEY    | The django secret key, set to a long, random sequence of characters |
| DATABASE_URL  | Where to find the database. Set to `postgresql://host:port/db` for a postgresql database |
| ALLOWED_HOSTS | Comma separated list of hostnames for this service, eg. `host1.example.org,host2.example.org` |
| CSRF_TRUSTED_ORIGINS | A list of trusted origins for unsafe requests  |
| CACHE_URL | Where to find the cache backend, format: redis://host:post/db . See [the django-environ docs](https://django-environ.readthedocs.io/en/latest/types.html#environ-env-cache-url) for more cache backends. |
| SENTRY_DSN | Where to send exceptions to |
| AWS_ACCESS_KEY_ID | Specifies an AWS access key associated with an IAM account |
| AWS_SECRET_ACCESS_KEY | Specifies the secret key associated with the access key. This is essentially the "password" for the access key |
| AWS_S3_REGION_NAME | Name of the AWS S3 region to use (eg. eu-west-1). |
| AWS_STORAGE_BUCKET_NAME | The name of the S3 bucket that will host the files. |
| WHATSAPP_CREATE_TEMPLATES | Should contentrepo submit templates to WhatsApp for creation. True/False |
| WHATSAPP_API_URL | WhatsApp API URL |
| WHATSAPP_ACCESS_TOKEN | WhatsApp API Token |
| FB_BUSINESS_ID | Business ID for Meta business manager |

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
