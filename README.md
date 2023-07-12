# Content Repository

This content repository allows easy content management via a headless CMS, using [wagtail](https://wagtail.io/) that is meant for web and various messaging platforms.

## Releases
The current LTS release is: 1.0

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
Run the following in a virtual environment
```bash
pip install -r requirements.txt
pip intsall -r requirements-dev.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

## API
The API documentation is available at the `/api/schema/swagger-ui/` endpoint.

### Authentication
Authentication is required to access the API. Session, basic, and token authentication is supported, but token authentication is advised.

To create an authentication token, you can do so via the Django Admin (available at the `/django-admin` endpoint), or by `POST`ing the username and password of the user you want to generate a token for to the `/api/v2/token/` endpoint.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
