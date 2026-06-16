import psycopg
import pytest

from trama.config import settings
from trama.cuit import validate_cuit
from trama.seed_demo import NETWORK_JSON, load_network, main


@pytest.fixture
def network():
    return load_network()


def _cleanup_seed_nodes(cuits):
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM operation WHERE node_id IN "
                "(SELECT id FROM node WHERE cuit = ANY(%s)) "
                "OR supplier_node_id IN "
                "(SELECT id FROM node WHERE cuit = ANY(%s))",
                (cuits, cuits),
            )
            cur.execute(
                "DELETE FROM document WHERE storage_ref = 'seed/x'"
            )
            cur.execute(
                "DELETE FROM node WHERE cuit = ANY(%s) "
                "AND NOT EXISTS (SELECT 1 FROM app_user WHERE node_id = node.id)",
                (cuits,),
            )
        conn.commit()


@pytest.fixture(autouse=True)
def reset_seed(network):
    cuits = [n["cuit"] for n in network["nodes"]]
    _cleanup_seed_nodes(cuits)
    yield
    _cleanup_seed_nodes(cuits)


def test_network_json_exists_and_loads(network):
    assert NETWORK_JSON.exists()
    assert isinstance(network["nodes"], list)
    assert isinstance(network["operations"], list)
    assert len(network["nodes"]) >= 1


def test_all_cuits_are_valid(network):
    for node in network["nodes"]:
        assert validate_cuit(node["cuit"]), f"invalid CUIT {node['cuit']}"


def test_all_node_roles_are_valid(network):
    for node in network["nodes"]:
        assert node["role"] in {"producer", "consumer", "both"}, node


def test_all_operation_cuits_resolve(network):
    cuits = {n["cuit"] for n in network["nodes"]}
    for op in network["operations"]:
        assert op["buyer_cuit"] in cuits, op
        assert op["supplier_cuit"] in cuits, op


def test_dry_run_does_not_touch_db(network):
    exit_code = main(["--dry-run"])
    assert exit_code == 0
    cuits = [n["cuit"] for n in network["nodes"]]
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM node WHERE cuit = ANY(%s)", (cuits,))
            (n,) = cur.fetchone()
    assert n == 0


def test_seed_inserts_nodes_and_operations(network):
    exit_code = main([])
    assert exit_code == 0
    cuits = [n["cuit"] for n in network["nodes"]]
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM node WHERE cuit = ANY(%s)", (cuits,))
            (n_nodes,) = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM operation o "
                "JOIN node b ON b.id = o.node_id "
                "WHERE b.cuit = ANY(%s)",
                (cuits,),
            )
            (n_ops,) = cur.fetchone()
    assert n_nodes == len(network["nodes"])
    assert n_ops == len(network["operations"])


def test_seed_is_idempotent(network):
    main([])
    main([])
    cuits = [n["cuit"] for n in network["nodes"]]
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM node WHERE cuit = ANY(%s)", (cuits,))
            (n,) = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM operation o "
                "JOIN node b ON b.id = o.node_id "
                "WHERE b.cuit = ANY(%s)",
                (cuits,),
            )
            (n_ops,) = cur.fetchone()
    assert n == len(network["nodes"])
    assert n_ops == len(network["operations"])


def test_wipe_actually_deletes_seed_nodes(network):
    main([])
    cuits = [n["cuit"] for n in network["nodes"]]
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM node WHERE cuit = ANY(%s) ORDER BY cuit",
                (cuits,),
            )
            ids_before = [r[0] for r in cur.fetchall()]
    main(["--wipe"])
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM node WHERE cuit = ANY(%s) ORDER BY cuit",
                (cuits,),
            )
            ids_after = [r[0] for r in cur.fetchall()]
    assert len(ids_after) == len(ids_before)
    assert set(ids_before).isdisjoint(set(ids_after))
