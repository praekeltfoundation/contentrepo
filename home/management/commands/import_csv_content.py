from django.core.management.base import BaseCommand

from home.utils import import_content_csv


class Command(BaseCommand):
    help = "Imports content via CSV"

    def add_arguments(self, parser):
        parser.add_argument("--path")
        parser.add_argument("--splitmessages", default="yes")
        parser.add_argument("--purge", default="no")
        parser.add_argument("--newline", default=False)
        parser.add_argument("--language_code", default="en")

    def handle(self, *args, **options):

        path = options["path"]
        splitmessages = options["splitmessages"]
        newline = options["newline"]
        purge = options["purge"]
        language_code = options["language_code"]

        with open(path, "rt") as file:
            import_content_csv(
                file=file,
                splitmessages=splitmessages,
                newline=newline,
                purge=purge,
                locale=language_code,
            )
