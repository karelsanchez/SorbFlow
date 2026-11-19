import hashlib

import pytest

from pyfast.io.experimental import load_breakthrough_csv


def load(path, **kwargs):
    settings = dict(
        experiment_id="experiment-7",
        species_name="arbitrary-solute",
        time_column="elapsed",
        concentration_column="outlet",
        time_unit="min",
        concentration_unit="mg/L",
    )
    return load_breakthrough_csv(path, **(settings | kwargs))


def test_explicit_units_uncertainties_bom_hash_and_untouched_source(tmp_path):
    path = tmp_path / "measurements.csv"
    original = (
        b"\xef\xbb\xbfelapsed,outlet,sigma,notes\r\n0,0,0.5,blank\r\n1.5,10,1.5,replicate A\r\n"
    )
    path.write_bytes(original)
    before = path.stat()
    result = load(path, std_column="sigma", std_unit="mg/L")
    assert result.experiment_id == "experiment-7"
    assert result.species_name == "arbitrary-solute"
    assert result.time_s == pytest.approx((0, 90))
    assert result.concentration_kg_m3 == pytest.approx((0, 0.01))
    assert result.std_kg_m3 == pytest.approx((0.0005, 0.0015))
    assert result.source_sha256 == hashlib.sha256(original).hexdigest()
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == before.st_mtime_ns


def test_explicit_delimiter_and_unused_multiline_metadata(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text('elapsed;outlet;notes\n0;1;"line one\n\nline two"\n2;5;end\n')
    result = load(path, delimiter=";")
    assert result.time_s == (0, 120)
    assert result.concentration_kg_m3 == pytest.approx((0.001, 0.005))
    assert result.std_kg_m3 is None


@pytest.mark.parametrize(
    "text,message",
    [
        ("", "headers"),
        ("elapsed,outlet,outlet\n0,0,0\n", "unique"),
        ("elapsed,outlet,\n0,0,0\n", "headers"),
        ("elapsed,wrong\n0,1\n", "missing"),
        ("elapsed,outlet\n0,1,extra\n", "row 2.*expected 2"),
        ("elapsed,outlet\n0\n", "row 2.*expected 2"),
        ("elapsed,outlet\n0,1\n\n1,2\n", "row 3.*blank"),
        ('elapsed,outlet\n0,"unterminated\n', "malformed CSV"),
        ("elapsed,outlet\n0,ND\n", "row 2.*outlet"),
        ("elapsed,outlet\n0,<0.1\n", "row 2.*outlet"),
        ("elapsed,outlet\n0,NaN\n", "row 2.*outlet"),
        ("elapsed,outlet\n0,Infinity\n", "row 2.*outlet"),
        ("elapsed,outlet\ntrue,1\n", "row 2.*elapsed"),
        ("elapsed,outlet\n0,1+2j\n", "row 2.*outlet"),
        ("elapsed,outlet\n-1,2\n", "row 2.*elapsed"),
        ("elapsed,outlet\n0,-1\n", "row 2.*outlet"),
        ("elapsed,outlet\n0,\n", "row 2.*outlet"),
        ("elapsed,outlet\n1,1\n0,2\n", "row 3.*strictly increase"),
        ("elapsed,outlet\n0,1\n0,2\n", "row 3.*strictly increase"),
    ],
)
def test_invalid_data_are_not_silently_cleaned(tmp_path, text, message):
    path = tmp_path / "bad.csv"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        load(path)
    assert path.read_text() == text


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"std_column": "sigma"}, "supplied together"),
        ({"std_unit": "mg/L"}, "supplied together"),
        ({"concentration_unit": "mol/L"}, "concentration_unit"),
        ({"concentration_unit": "ppm"}, "concentration_unit"),
        ({"time_unit": "mg"}, "time_unit"),
        ({"std_column": "sigma", "std_unit": "mol/L"}, "std_unit"),
        ({"time_column": ""}, "time_column"),
        ({"time_column": "outlet"}, "distinct"),
        ({"delimiter": "||"}, "delimiter"),
        ({"delimiter": "\n"}, "delimiter"),
    ],
)
def test_explicit_mapping_and_units_required(tmp_path, kwargs, message):
    path = tmp_path / "units.csv"
    path.write_text("elapsed,outlet,sigma\n0,1,0.1\n")
    with pytest.raises(ValueError, match=message):
        load(path, **kwargs)


def test_standard_deviation_must_be_positive_and_encoding_explicit(tmp_path):
    path = tmp_path / "sigma.csv"
    path.write_text("elapsed,outlet,sigma\n0,1,0\n")
    with pytest.raises(ValueError, match="row 2.*sigma.*positive"):
        load(path, std_column="sigma", std_unit="mg/L")
    path.write_bytes(b"elapsed,outlet\n0,1\xff\n")
    with pytest.raises(ValueError, match="UTF-8"):
        load(path)
