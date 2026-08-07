# Database Migrations

This directory contains the migration files for managing database schema changes in the project. 

## Applying Migrations

To apply migrations, use the following command:

```
alembic upgrade head
```

This command will apply all pending migrations to the database.

## Creating New Migrations

To create a new migration after making changes to the database models, run:

```
alembic revision --autogenerate -m "Description of changes"
```

Replace `"Description of changes"` with a brief summary of the modifications made.

## Rollback Migrations

To rollback the last applied migration, use:

```
alembic downgrade -1
```

## Notes

- Ensure that your database is backed up before applying or rolling back migrations.
- Review the generated migration scripts to confirm that they accurately reflect the intended changes.