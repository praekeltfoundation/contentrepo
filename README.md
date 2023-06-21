# Content Repository

This content repository allows easy content management via a headless CMS, using [wagtail](https://wagtail.io/) that is meant for web and various messaging platforms.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install content repository.

```bash
pip install contentrepo
```

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
