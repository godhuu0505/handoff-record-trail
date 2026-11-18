"""Trace fictional correction histories and verify the demo scenarios."""

import json
from importlib.metadata import version

import relate


TRACE = """
MATCH (share:Share {id: $share_id})-[:REFERENCES]->(pinned:CareVersion)
MATCH (pinned)-[:FOR_PET]->(original:Pet)
MATCH path = (pinned)-[:SUPERSEDED_BY*0..]->(head:CareVersion)
WHERE NOT EXISTS { MATCH (head)-[:SUPERSEDED_BY]->(:CareVersion) }
OPTIONAL MATCH (head)-[:FOR_PET]->(pet:Pet)
WITH share, pinned, original, path, head, collect(pet) AS pets
RETURN share.id AS share_id, share.text AS shared_text,
       pinned.id AS pinned_id, original.id AS pinned_pet_id,
       head.id AS head_id, head.status AS head_status,
       size(pets) AS head_pet_link_count,
       CASE WHEN size(pets) = 1 THEN pets[0].id END AS head_pet_id,
       CASE WHEN size(pets) = 1 THEN pets[0].name END AS head_pet_name,
       [node IN nodes(path) | node.id] AS version_path
ORDER BY version_path
"""


def trace(db, share_id):
    rows = db.execute(TRACE, {"share_id": share_id}).data()
    if not rows:
        return {"status": "unavailable", "paths": [], "current_heads": []}

    first = rows[0]
    heads_by_id = {
        row["head_id"]: {
            "version_id": row["head_id"],
            "pet_id": row["head_pet_id"],
            "pet_name": row["head_pet_name"],
            "record_status": row["head_status"],
        }
        for row in rows
    }
    heads = list(heads_by_id.values())
    if any(row["head_pet_link_count"] != 1 or row["head_pet_id"] is None for row in rows):
        status = "needs_confirmation"
        reason = "a_current_version_has_no_unique_pet"
    elif len(heads) != 1:
        status = "needs_confirmation"
        reason = "multiple_current_versions"
    elif heads[0]["pet_id"] != first["pinned_pet_id"]:
        status = "needs_confirmation"
        reason = "the_shared_record_now_points_to_a_different_pet"
    elif heads[0]["record_status"] != "completed":
        status = "needs_confirmation"
        reason = "completion_is_unconfirmed"
    else:
        status = "matched"
        reason = "one_current_version_for_the_original_pet"

    return {
        "status": status,
        "reason": reason,
        "shared_text": first["shared_text"],
        "shared_version_id": first["pinned_id"],
        "shared_pet_id": first["pinned_pet_id"],
        "paths": [row["version_path"] for row in rows],
        "current_heads": heads,
    }


def verify(db, label, *, status, reason, paths, expected_heads):
    result = trace(db, "share-01")
    assert result["shared_text"] == "Breakfast recorded as completed for Mochi."
    assert result["shared_version_id"] == "r1"
    assert result["shared_pet_id"] == "pet-a"
    assert result["status"] == status
    assert result["reason"] == reason
    assert result["paths"] == paths
    observed_heads = [
        (head["version_id"], head["pet_id"], head["record_status"])
        for head in result["current_heads"]
    ]
    assert observed_heads == expected_heads
    assert {head["pet_name"] for head in result["current_heads"]} == {"Mochi"}
    return {"case": label, "trace": result}


DEMO_WRITES = (
    """
            CREATE (a:Pet {id: 'pet-a', name: 'Mochi'}),
                   (b:Pet {id: 'pet-b', name: 'Mochi'}),
                   (s:Share {id: 'share-01', text: 'Breakfast recorded as completed for Mochi.'}),
                   (r1:CareVersion {id: 'r1', status: 'completed'}),
                   (other:CareVersion {id: 'unrelated', status: 'completed'}),
                   (s)-[:REFERENCES]->(r1), (r1)-[:FOR_PET]->(a),
                   (other)-[:FOR_PET]->(a)
        """,
    """
            MATCH (r1:CareVersion {id: 'r1'}), (b:Pet {id: 'pet-b'})
            CREATE (r2:CareVersion {id: 'r2', status: 'completed'}),
                   (r1)-[:SUPERSEDED_BY]->(r2), (r2)-[:FOR_PET]->(b)
        """,
    """
            MATCH (r1:CareVersion {id: 'r1'}), (a:Pet {id: 'pet-a'})
            CREATE (r3:CareVersion {id: 'r3', status: 'unconfirmed'}),
                   (r1)-[:SUPERSEDED_BY]->(r3), (r3)-[:FOR_PET]->(a)
        """,
    """
            MATCH (r2:CareVersion {id: 'r2'}), (r3:CareVersion {id: 'r3'}),
                  (a:Pet {id: 'pet-a'})
            CREATE (r4:CareVersion {id: 'r4', status: 'unconfirmed'}),
                   (r2)-[:SUPERSEDED_BY]->(r4), (r3)-[:SUPERSEDED_BY]->(r4),
                   (r4)-[:FOR_PET]->(a)
        """,
    """
            MATCH (r4:CareVersion {id: 'r4'}), (a:Pet {id: 'pet-a'})
            CREATE (r5:CareVersion {id: 'r5', status: 'completed'}),
                   (r6:CareVersion {id: 'r6', status: 'completed'}),
                   (r4)-[:SUPERSEDED_BY]->(r5), (r5)-[:FOR_PET]->(a),
                   (r4)-[:SUPERSEDED_BY]->(r6)
        """,
)


def run_demo():
    with relate.connect(":memory:") as db:
        db.execute(DEMO_WRITES[0])
        cases = [
            verify(
                db, "before_correction", status="matched",
                reason="one_current_version_for_the_original_pet",
                paths=[["r1"]], expected_heads=[("r1", "pet-a", "completed")],
            )
        ]
        db.execute(DEMO_WRITES[1])
        cases.append(
            verify(
                db, "correction_to_another_pet_with_same_name", status="needs_confirmation",
                reason="the_shared_record_now_points_to_a_different_pet",
                paths=[["r1", "r2"]], expected_heads=[("r2", "pet-b", "completed")],
            )
        )

        db.execute(DEMO_WRITES[2])
        cases.append(
            verify(
                db, "unresolved_correction_branches", status="needs_confirmation",
                reason="multiple_current_versions", paths=[["r1", "r2"], ["r1", "r3"]],
                expected_heads=[("r2", "pet-b", "completed"), ("r3", "pet-a", "unconfirmed")],
            )
        )

        db.execute(DEMO_WRITES[3])
        cases.append(
            verify(
                db, "branches_converge_on_explicit_correction", status="needs_confirmation",
                reason="completion_is_unconfirmed",
                paths=[["r1", "r2", "r4"], ["r1", "r3", "r4"]],
                expected_heads=[("r4", "pet-a", "unconfirmed")],
            )
        )

        db.execute(DEMO_WRITES[4])
        missing_pet = trace(db, "share-01")
        assert missing_pet["status"] == "needs_confirmation"
        assert missing_pet["reason"] == "a_current_version_has_no_unique_pet"
        assert missing_pet["shared_version_id"] == "r1"
        assert [(head["version_id"], head["pet_id"]) for head in missing_pet["current_heads"]] == [
            ("r5", "pet-a"), ("r6", None)
        ]
        assert len(missing_pet["paths"]) == 4
        cases.append({"case": "a_branch_has_no_pet_link", "trace": missing_pet})

        unknown = trace(db, "missing")
        assert unknown == {"status": "unavailable", "paths": [], "current_heads": []}
        cases.append({"case": "unknown_share", "trace": unknown})
        return cases


if __name__ == "__main__":
    print(json.dumps({"relate_db_version": version("relate-db"), "cases": run_demo()}, indent=2))
