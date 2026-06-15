import pytest

from slurm_job_doctor.parsers.unit_parser import (
    format_memory_mb,
    format_seconds,
    parse_memory_mb,
    parse_reqmem,
    parse_time_seconds,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("16G", 16384),
        ("16000M", 16000),
        ("1T", 1048576),
        ("15700M", 15700),
        ("16Gn", 16384),
        ("4Gc", 4096),
        ("16GB", 16384),
        ("15.5G", 15872),
        ("16384", 16384),
        ("512K", 0),  # 0.5 MiB rounds to 0
        ("0", 0),
    ],
)
def test_parse_memory_mb(value, expected):
    assert parse_memory_mb(value) == expected


@pytest.mark.parametrize("value", [None, "", "Unknown", "INVALID", "N/A"])
def test_parse_memory_none(value):
    assert parse_memory_mb(value) is None


def test_parse_reqmem_keeps_scope():
    assert parse_reqmem("16Gn") == (16384, "node")
    assert parse_reqmem("4Gc") == (4096, "cpu")
    assert parse_reqmem("16G") == (16384, None)


def test_parse_memory_invalid_raises():
    with pytest.raises(ValueError):
        parse_memory_mb("sixteen gigs")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("02:00:00", 7200),
        ("1-02:00:00", 93600),
        ("00:12:31", 751),
        ("12:31", 751),
        ("01:00:00", 3600),
        ("60", 3600),
        ("1-00", 86400),
        ("1-02:30", 95400),
        ("0", 0),
    ],
)
def test_parse_time_seconds(value, expected):
    assert parse_time_seconds(value) == expected


@pytest.mark.parametrize("value", [None, "", "UNLIMITED", "INVALID", "Partition_Limit"])
def test_parse_time_none(value):
    assert parse_time_seconds(value) is None


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError):
        parse_time_seconds("two hours")


@pytest.mark.parametrize(
    "mib,expected",
    [(16384, "16G"), (24576, "24G"), (15700, "15700M"), (49152, "48G"), (0, "0M")],
)
def test_format_memory_mb(mib, expected):
    assert format_memory_mb(mib) == expected


@pytest.mark.parametrize(
    "seconds,expected",
    [(7200, "02:00:00"), (93600, "1-02:00:00"), (751, "00:12:31"), (3600, "01:00:00")],
)
def test_format_seconds(seconds, expected):
    assert format_seconds(seconds) == expected


def test_roundtrip_time_and_memory():
    assert parse_time_seconds(format_seconds(93600)) == 93600
    assert parse_memory_mb(format_memory_mb(24576)) == 24576
