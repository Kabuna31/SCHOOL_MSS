"""Keep compatible with the historical migrations that import this helper."""

from collections import defaultdict


def backfill_school_fields(app_label, model_relations, apps, schema_editor):
    """Populate new school FKs from related records or an unambiguous sole school."""
    alias = schema_editor.connection.alias
    School = apps.get_model("administration", "School")
    school_ids = list(
        School._base_manager.using(alias).values_list("pk", flat=True)[:2]
    )
    sole_school_id = school_ids[0] if len(school_ids) == 1 else None

    for model_name, relation_paths in model_relations:
        Model = apps.get_model(app_label, model_name)
        manager = Model._base_manager.using(alias)
        rows = manager.filter(school__isnull=True).values_list(
            "pk", *relation_paths
        )
        batches = defaultdict(list)
        unresolved = []

        for row in rows.iterator(chunk_size=1000):
            pk, *related_school_ids = row
            candidates = {school_id for school_id in related_school_ids if school_id}
            if len(candidates) > 1:
                raise RuntimeError(
                    f"{app_label}.{model_name} row {pk} links to multiple schools "
                    f"({sorted(candidates)}); assign its school explicitly before "
                    "retrying this migration."
                )

            school_id = next(iter(candidates), sole_school_id)
            if school_id is None:
                unresolved.append(pk)
                continue

            batches[school_id].append(pk)
            if len(batches[school_id]) >= 1000:
                manager.filter(
                    pk__in=batches[school_id], school_id__isnull=True
                ).update(school_id=school_id)
                batches[school_id].clear()

        if unresolved:
            raise RuntimeError(
                f"Cannot safely assign a school to {app_label}.{model_name} rows "
                f"{unresolved[:10]}. The row has no related school and the database "
                "does not contain exactly one School record. Resolve ownership "
                "explicitly, then retry this migration."
            )

        for school_id, pks in batches.items():
            if pks:
                manager.filter(
                    pk__in=pks, school_id__isnull=True
                ).update(school_id=school_id)
