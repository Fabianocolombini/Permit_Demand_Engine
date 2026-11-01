"""TOM/SAM classify keep/exclude signals."""

from src.classify.rules import SAM_CATEGORIES, classify_text, is_sam


def test_sam_categories():
    assert SAM_CATEGORIES == {
        "res_new_plumbing",
        "res_repipe",
        "res_remodel_plumbing",
        "irrigation",
        "pool_spa",
    }


def test_plum_code_is_sam():
    cat, method, conf = classify_text("PLUM", "SINGLE FAM RES", "SEWER LINE")
    assert cat == "res_new_plumbing"
    assert is_sam(cat)
    assert method == "regex"
    assert conf >= 0.75


def test_repipe_beats_generic_plum():
    cat, method, _ = classify_text("PLUM", None, "whole house repipe")
    assert cat == "res_repipe"
    assert is_sam(cat)


def test_pool_spa():
    cat, method, _ = classify_text("Pool_Spa", None, "new swimming pool")
    assert cat == "pool_spa"
    assert is_sam(cat)


def test_irrigation():
    cat, method, _ = classify_text("BLDG", None, "lawn sprinkler irrigation system")
    assert cat == "irrigation"
    assert is_sam(cat)


def test_new_residential_application_type_is_sam():
    """Miami-Dade ApplicationTypeDescription NEW + SFR use → SAM (implied rough-in)."""
    cat, method, _ = classify_text(
        "BLDG",
        "NEW | SINGLE FAM RES-CLUST-ZERO LOT-TOWN HOUSE",
        "NEW SINGLE FAMILY RESIDENCE",
    )
    assert cat == "res_new_plumbing"
    assert is_sam(cat)
    assert method == "regex"


def test_new_sfr_language_is_sam():
    cat, method, _ = classify_text("BLDG", None, "new single family home")
    assert cat == "res_new_plumbing"
    assert is_sam(cat)


def test_new_townhouse_is_sam():
    cat, method, _ = classify_text("MBLD", "NEW", "new townhouse building")
    assert cat == "res_new_plumbing"
    assert is_sam(cat)


def test_orlando_building_permit_new_is_sam():
    cat, method, _ = classify_text("Building Permit", "New", None)
    assert cat == "res_new_plumbing"
    assert is_sam(cat)


def test_manatee_single_family_new_either_order_is_sam():
    cat, method, _ = classify_text(
        "Residential",
        "Residential | Single Family",
        "PULTE HOME COMPANY LLC NEW RESIDENCE",
    )
    assert cat == "res_new_plumbing"
    assert is_sam(cat)


def test_orlando_mechanical_new_not_sam():
    cat, method, _ = classify_text("Mechanical Permit", "New", None)
    assert not is_sam(cat)


def test_exclude_roof_on_sfr_not_sam():
    cat, method, _ = classify_text(
        "BLDG",
        "RE-ROOF/REPAIR | SINGLE FAM RES",
        "RE-ROOF TILE",
    )
    assert cat == "other"
    assert not is_sam(cat)
    assert method.startswith("excluded_")


def test_exclude_windows_on_sfr_not_sam():
    cat, method, _ = classify_text(
        "BLDG",
        "ENT REPLACEMENT | SINGLE FAM RES",
        "WINDOWS/DOORS",
    )
    assert cat == "other"
    assert not is_sam(cat)


def test_exclude_ac_only():
    cat, method, _ = classify_text(
        "Mechanical Express",
        None,
        "Replace existing 3 ton system like for like",
    )
    assert cat == "other"
    assert not is_sam(cat)
    assert method.startswith("excluded_")


def test_exclude_fence():
    cat, method, _ = classify_text("BLDG", "FENCE NOMASONRY", "INSTALL FENCE")
    assert cat == "other"
    assert not is_sam(cat)


def test_bare_bldg_sfr_without_new_not_auto_sam():
    """Alteration on SFR without NEW / plumbing should not enter SAM."""
    cat, method, _ = classify_text(
        "BLDG",
        "ALTER - INTERIOR | SINGLE FAM RES",
        "INTERIOR ALTERATION ONLY",
    )
    assert not is_sam(cat)


def test_water_heater_not_sam():
    cat, method, _ = classify_text("PLUM", None, "water heater replacement")
    assert cat == "res_water_heater"
    assert not is_sam(cat)


def test_plumbing_remodel_is_sam():
    cat, method, _ = classify_text("Plumbing", None, "plumbing remodel bath")
    assert cat in {"res_remodel_plumbing", "res_new_plumbing"}
    assert is_sam(cat)
