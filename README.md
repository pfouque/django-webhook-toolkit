# django-webhook-toolkit - Django Webhook management made easy

[![CI tests](https://github.com/pfouque/django-webhook-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/pfouque/django-webhook-toolkit/actions/workflows/test.yml)
[![codecov](https://codecov.io/github/pfouque/django-webhook-toolkit/branch/master/graph/badge.svg?token=GWGDR6AR6D)](https://codecov.io/github/pfouque/django-webhook-toolkit)
[![Documentation](https://img.shields.io/static/v1?label=Docs&message=READ&color=informational&style=plastic)](https://github.com/pfouque/django-webhook-toolkit#settings)
[![MIT License](https://img.shields.io/static/v1?label=License&message=MIT&color=informational&style=plastic)](https://github.com/pfouque/django-webhook-toolkit/LICENSE)

## Introduction

django-webhook-toolkit helps you send and receive webhooks.

## Resources

-   Package on PyPI: [https://pypi.org/project/django-webhook-toolkit/](https://pypi.org/project/django-webhook-toolkit/)
-   Project on Github: [https://github.com/pfouque/django-webhook-toolkit](https://github.com/pfouque/django-webhook-toolkit)

## Features

-   Provides "abstract" Model for receiving webhooks
-   Provides "abstract" Models to send webhooks

## Requirements

-   Django >=4.2
-   Python >=3.10

## How to

1. Install
    ```
    $ pip install "django-webhook-toolkit"
    ```

### How to receive webhooks

2. Create your model inheriting from `AbstractWebhookEvent` (and implement process_payload + get_signing_secrets):

    ```python
    class AcmeWebhookEvent(AbstractWebhookEvent):

        @classmethod
        def get_signing_secrets(cls, request):
            return ["whsec_..."]

        def process_payload(self) -> None:
            # Do whetever needs to be done
    ```

3. Wire a receiver view to your URLconf:

    ```python
    from webhook_toolkit.receiver.views import WebhookReceiverView

    from .models import AcmeWebhookEvent

    class AcmeWebhookReceiverView(WebhookReceiverView):
        webhook_event_model = AcmeWebhookEvent
        signature_mechanism = "standardwebhooks"
    ```

    ```python
    urlpatterns = [
        path("webhooks/acme/", AcmeWebhookReceiverView.as_view(), name="acme-webhook"),
    ]
    ```

4. Then migrate your app to create the database table:
    ```manage.py migrate my_app```

5. 🎉 Voila!

### How to send webhooks

1. Add the sender app to your Django project:

    ```
    INSTALLED_APPS = [
        # ...
        "webhook_toolkit.sender",
        # ...
    ]
    ```

2. Then migrate to create the tables:
    ```manage.py migrate```

## Settings

You can add settings to your project’s settings.py either as a single `WEBHOOKS` dict, or by breaking out individual settings prefixed with WEBHOOKS_. So this settings dict:

```
WEBHOOKS = {
    "SENDER_MAX_RETRY": 10,
}
```
…is equivalent to these individual settings:

```
WEBHOOKS_SENDER_MAX_RETRY = 10
```

### Available settings

-   `WEBHOOKS_SENDER_MAX_RETRY`: (default: 10) Max retry attempts before aborting.
-   `WEBHOOKS_RECEIVER_DEFAULT_RETENTION_DAYS`: (default: 10) Auto-delete receiver events older than N days.
-   `WEBHOOKS_RECEIVER_TIMESTAMP_TOLERANCE`: (default: 300) Allowed timestamp skew in seconds.

Available signature mechanisms: `standardwebhooks`, `github-hmac-sha256`, `slack-v0`.
Per-sender settings: `WebhookSubscription.signature_mechanism` and `WebhookSubscription.get_signing_secrets()`.
Per-receiver settings: `WebhookReceiverView.signature_mechanism` and `AbstractWebhookEvent.get_signing_secrets()`.

## Contribute

### Principles

-   Simple for developers to get up-and-running
-   Consistent style (`ruff`)
-   Future-proof (`pyupgrade`)
-   Full type hinting (`mypy`)

### Coding style

We use [prek](https://github.com/j178/prek) to run code quality tools.
[Install prek](https://github.com/j178/prek) however you like (e.g.
`pip install prek` with your system python) then set up prek to run every time you
commit with:

```bash
> prek install
```

You can then run all tools:

```bash
> prek run --all-files
```

It includes the following:

-   `uv` for dependency management
-   `Ruff`, `black` and `pyupgrade` linting
-   `mypy` for type checking
-   `Github Actions` for builds and CI

There are default config files for the linting and mypy.

### Tests

#### Tests package

The package tests themselves are _outside_ of the main library code, in a package that is itself a
Django app (it contains `models`, `settings`, and any other artifacts required to run the tests
(e.g. `urls`).) Where appropriate, this test app may be runnable as a Django project - so that
developers can spin up the test app and see what admin screens look like, test migrations, etc.

#### Running tests

The tests themselves use `pytest` as the test runner. If you have installed the `uv` environment,
you can run them thus:

```
$ uv run pytest
```

or

```
$ uv venv
$ source .venv/bin/activate
(.venv) $ pytest
```

#### CI

- `.github/workflows/lint.yml`: defines and ensure coding rules on Github.

- `.github/workflows/test.yml`: Runs tests on all compatible combinations of Django (4.2+) & Python (3.8+)in a Github matrix.

- `.github/workflows/coverage.yml`: Calculates the coverage on an up to date version.
