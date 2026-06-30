from django.core.management.base import BaseCommand
from django.db import connection, transaction

class Command(BaseCommand):
    help = (
        'Deletes rows from the orphaned `concierge_conciergerequest` table '
        'that are linked to specific ticket IDs.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'ticket_ids',
            nargs='+',
            type=int,
            help='One or more ticket IDs to clean from the orphaned table.',
        )

    def handle(self, *args, **options):
        ticket_ids = options['ticket_ids']
        table_name = 'concierge_conciergerequest'
        column_name = 'ticket_id'

        self.stdout.write(
            self.style.WARNING(
                f"This command will attempt to delete rows from the '{table_name}' table."
            )
        )
        self.stdout.write(f"Tickets to process: {ticket_ids}")

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    if not ticket_ids:
                        self.stdout.write("No ticket IDs provided. Exiting.")
                        return

                    # Using a parameterized query to prevent SQL injection
                    # The parameter style for SQLite is 'qmark' (?)
                    placeholders = ', '.join(['?'] * len(ticket_ids))
                    sql_query = f"DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})"

                    cursor.execute(sql_query, ticket_ids)

                    rows_deleted = cursor.rowcount

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {rows_deleted} row(s) from '{table_name}' "
                    f"for the specified ticket IDs."
                )
            )
            self.stdout.write(
                "You should now be able to delete the original tickets via the admin or application interface."
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"An error occurred: {e}")
            )
            self.stderr.write(
                f"The operation was rolled back. Please ensure the table '{table_name}' and column '{column_name}' exist."
            )
