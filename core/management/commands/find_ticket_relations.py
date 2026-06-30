from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Finds all tables in the database that have a foreign key to the tickets_ticket table.'

    def handle(self, *args, **options):
        target_table = 'tickets_ticket'
        self.stdout.write(f"Searching for foreign keys pointing to '{target_table}'...")

        found_relations = False
        with connection.cursor() as cursor:
            # Get a list of all tables in the database
            all_tables = connection.introspection.table_names(cursor)

            for table_name in all_tables:
                if table_name == target_table:
                    continue

                try:
                    # Get the constraints for the current table
                    constraints = connection.introspection.get_constraints(cursor, table_name)
                    for name, details in constraints.items():
                        # Check if it's a foreign key
                        if details['foreign_key']:
                            fk_table, fk_column = details['foreign_key']
                            if fk_table == target_table:
                                found_relations = True
                                self.stdout.write(self.style.SUCCESS(
                                    f"  Found relation in table '{table_name}':"
                                ))
                                self.stdout.write(f"    - Constraint Name: {name}")
                                self.stdout.write(f"    - Column(s): {details['columns']}")
                                self.stdout.write(f"    - Points to: {fk_table}({fk_column})")

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Could not inspect table '{table_name}': {e}"))

        if not found_relations:
            self.stdout.write(self.style.WARNING(f"No foreign key relationships pointing to '{target_table}' were found."))
        else:
            self.stdout.write("\nInspection complete.")
