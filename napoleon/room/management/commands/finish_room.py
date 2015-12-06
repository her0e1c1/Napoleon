import datetime

from django.core.management.base import BaseCommand

from napoleon.room.models import Room


class Command(BaseCommand):
    help = 'Finish rooms if they are created one day ago by default'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=1, help="Specify days")

    def handle(self, *args, **options):
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=options["days"])
        query = Room.objects.filter(
            created_at__lte=now - delta,
            finished=False,
        )
        query.update(finished=True)
        self.stdout.write('Successfully finish rooms')
