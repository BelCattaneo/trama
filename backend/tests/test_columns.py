from trama.parsing.columns import REQUIRED_FIELDS, canonicalize_columns


def test_standard_three_columns():
    result = canonicalize_columns(["Producto", "Cantidad", "Unidad"])
    assert result == {
        "Producto": "product",
        "Cantidad": "quantity",
        "Unidad": "unit",
    }


def test_required_fields_export():
    assert REQUIRED_FIELDS == {"product", "quantity"}


def test_case_insensitive():
    assert canonicalize_columns(["PRODUCTO"]) == {"PRODUCTO": "product"}
    assert canonicalize_columns(["producto"]) == {"producto": "product"}
    assert canonicalize_columns(["ProDuCtO"]) == {"ProDuCtO": "product"}


def test_accent_insensitive():
    assert canonicalize_columns(["Descripción"]) == {"Descripción": "product"}
    assert canonicalize_columns(["Presentación"]) == {"Presentación": "unit"}


def test_rioplatense_synonyms_for_product():
    assert canonicalize_columns(["Mercadería"]) == {"Mercadería": "product"}
    assert canonicalize_columns(["verdura"]) == {"verdura": "product"}
    assert canonicalize_columns(["Fruta"]) == {"Fruta": "product"}
    assert canonicalize_columns(["articulo"]) == {"articulo": "product"}


def test_rioplatense_synonyms_for_quantity():
    assert canonicalize_columns(["Kg"]) == {"Kg": "quantity"}
    assert canonicalize_columns(["kilos"]) == {"kilos": "quantity"}
    assert canonicalize_columns(["cant"]) == {"cant": "quantity"}
    assert canonicalize_columns(["unidades"]) == {"unidades": "quantity"}


def test_rioplatense_synonyms_for_unit():
    assert canonicalize_columns(["medida"]) == {"medida": "unit"}
    assert canonicalize_columns(["Presentación"]) == {"Presentación": "unit"}
    assert canonicalize_columns(["u/medida"]) == {"u/medida": "unit"}


def test_whitespace_bordered_headers():
    assert canonicalize_columns([" Producto "]) == {" Producto ": "product"}
    assert canonicalize_columns(["\tCantidad\n"]) == {"\tCantidad\n": "quantity"}


def test_unrecognized_headers_omitted():
    result = canonicalize_columns(["Productor", "Cantidad", "Notas", "Precio"])
    assert result == {"Cantidad": "quantity"}
    assert "Productor" not in result
    assert "Notas" not in result


def test_empty_headers_list():
    assert canonicalize_columns([]) == {}


def test_empty_string_header():
    assert canonicalize_columns([""]) == {}


def test_partial_match_does_not_count():
    # "productores" contains "producto" but is not in the synonym list
    assert canonicalize_columns(["Productores"]) == {}


def test_required_fields_missing_still_returns_partial():
    # Only unit matches; caller checks REQUIRED_FIELDS
    result = canonicalize_columns(["unidad"])
    assert result == {"unidad": "unit"}
    assert not REQUIRED_FIELDS.issubset(set(result.values()))


def test_unidades_maps_to_quantity_not_unit():
    # YAML order: 'unidades' lives under quantity, not unit.
    # Pins the ambiguity resolution: first match wins, in YAML order.
    assert canonicalize_columns(["unidades"]) == {"unidades": "quantity"}


def test_first_match_wins_on_ambiguity():
    # Both 'producto' and 'productos' are product synonyms — both win cleanly.
    assert canonicalize_columns(["producto", "productos"]) == {
        "producto": "product",
        "productos": "product",
    }


def test_mixed_real_world_planilla():
    result = canonicalize_columns(
        [
            "Mercadería",
            "Kg",
            "Presentación",
            "Productor",
            "Precio unitario",
            "Notas",
        ]
    )
    assert result == {
        "Mercadería": "product",
        "Kg": "quantity",
        "Presentación": "unit",
    }
