from django.core.management.base import BaseCommand
from django.db import transaction

from ultimate_ladder import rating


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = ("Recompute the ratings and the statistics of all the players by replaying "
            "all the completed games, starting from the initial score of each player.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Display the new scores without saving them.")

    def handle(self, *args, dry_run=False, **options):
        try:
            with transaction.atomic():
                changes = rating.recompute_all()
                self.report(changes)
                if dry_run:
                    raise DryRun
        except DryRun:
            self.stdout.write(self.style.WARNING("Dry run: nothing was saved."))
            return
        self.stdout.write(self.style.SUCCESS(f"Recomputed the ratings of {len(changes)} players."))

    def report(self, changes):
        by_owner = {}
        for player, old, new in changes:
            by_owner.setdefault(player.owner.username, []).append((player, old, new))
        for owner, players in sorted(by_owner.items()):
            self.stdout.write(f"{owner}:")
            for player, old, new in sorted(players, key=lambda c: -c[2]):
                self.stdout.write(f"  {player.name:<25} {old:>6} -> {new:>6}")
