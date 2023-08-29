from fractions import Fraction
from pandas.errors import EmptyDataError, DataError
from pathlib import Path
import pytest

from votekit.ballot import Ballot
from votekit.cvr_loaders import load_csv, load_blt
from votekit.pref_profile import PreferenceProfile


BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "data/csv/"
BLT_DIR = BASE_DIR / "data/txt/"


def is_equal(b1: list[Ballot], b2: list[Ballot]) -> bool:
    if len(b1) != len(b2):
        return False
    for b in b1:
        if b not in b2:
            return False
    return True


def test_empty_csv():
    with pytest.raises(EmptyDataError):
        load_csv(CSV_DIR / "empty.csv", id_col=0)


def test_undervote():
    prof = load_csv(CSV_DIR / "undervote.csv", id_col=0)
    a = Ballot(
        id=None, ranking=[{"c"}, {None}, {None}], weight=Fraction(1), voters={"a"}
    )
    correct_prof = PreferenceProfile(ballots=[a])
    assert correct_prof.ballots == prof.ballots
    # assert correct_prof.ballots[0].ranking == prof.ballots[0].ranking


def test_only_cols():
    with pytest.raises(EmptyDataError):
        load_csv(CSV_DIR / "only_cols.csv", id_col=0)


def test_invalid_path():
    with pytest.raises(FileNotFoundError):
        load_csv("fake_path.csv", id_col=0)


def test_duplicates_candidates():
    prof = load_csv(CSV_DIR / "dup_cands.csv", id_col=0)
    # assert len(prof.ballots) == 3
    abe = Ballot(ranking=[{"b"}, {"c"}, {"c"}], weight=Fraction(1), voters={"abe"})
    don = Ballot(ranking=[{"a"}, {"c"}, {"c"}], weight=Fraction(1), voters={"don"})
    carrie = Ballot(
        ranking=[{"c"}, {"c"}, {"c"}], weight=Fraction(1), voters={"carrie"}
    )
    correct_prof = PreferenceProfile(ballots=[abe, don, carrie])
    assert is_equal(prof.ballots, correct_prof.ballots)


def test_single_row():
    prof = load_csv(CSV_DIR / "single_row.csv", id_col=0)
    a = Ballot(ranking=[{"b"}, {"c"}, {"d"}], weight=Fraction(1), voters={"a"})
    correct_prof = PreferenceProfile(ballots=[a])
    assert is_equal(prof.ballots, correct_prof.ballots)


def test_multiple_undervotes():
    prof = load_csv(CSV_DIR / "mult_undervote.csv", id_col=0)
    abc = Ballot(
        ranking=[{"c"}, {None}, {None}],
        weight=Fraction(3),
        voters={"abe", "ben", "carl"},
    )
    dave = Ballot(ranking=[{None}, {"a"}, {None}], weight=Fraction(1), voters={"dave"})
    correct_prof = PreferenceProfile(ballots=[abc, dave])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_different_undervotes():
    prof = load_csv(CSV_DIR / "diff_undervote.csv", id_col=0)
    a = Ballot(ranking=[{"c"}, {None}, {"b"}], weight=Fraction(1), voters={"a"})
    b = Ballot(ranking=[{None}, {"d"}, {None}], weight=Fraction(1), voters={"b"})
    c = Ballot(ranking=[{"e"}, {None}, {"e"}], weight=Fraction(1), voters={"c"})
    correct_prof = PreferenceProfile(ballots=[a, b, c])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_duplicate_ballots():
    prof = load_csv(CSV_DIR / "dup_ballots.csv", id_col=0)
    a = Ballot(ranking=[{"b"}, {"c"}, {"c"}], weight=Fraction(1), voters={"abe"})
    dc = Ballot(
        ranking=[{"c"}, {"c"}, {"c"}], weight=Fraction(2), voters={"don", "carrie"}
    )
    correct_prof = PreferenceProfile(ballots=[a, dc])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_combo():
    prof = load_csv(CSV_DIR / "combo.csv", id_col=0)
    abc = Ballot(
        ranking=[{"b"}, {"c"}, {"c"}],
        weight=Fraction(3),
        voters={"abe", "ben", "carrie"},
    )
    de = Ballot(
        ranking=[{"c"}, {None}, {None}], weight=Fraction(2), voters={"don", "ed"}
    )
    correct_prof = PreferenceProfile(ballots=[abc, de])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_diff_candidates():
    prof = load_csv(CSV_DIR / "diff_cands.csv", id_col=0)
    abe = Ballot(ranking=[{"a"}, {"b"}, {"c"}], voters={"abe"}, weight=Fraction(1))
    don = Ballot(ranking=[{"d"}, {"e"}, {"f"}], weight=Fraction(1), voters={"don"})
    carrie = Ballot(
        ranking=[{"g"}, {"h"}, {"i"}], weight=Fraction(1), voters={"carrie"}
    )
    correct_prof = PreferenceProfile(ballots=[abe, don, carrie])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_same_candidates():
    prof = load_csv(CSV_DIR / "same_cands.csv", id_col=0)
    abe = Ballot(ranking=[{"a"}, {"b"}, {"c"}], voters={"abe"}, weight=Fraction(1))
    don = Ballot(ranking=[{"c"}, {"b"}, {"a"}], weight=Fraction(1), voters={"don"})
    carrie = Ballot(
        ranking=[{"a"}, {"c"}, {"b"}], weight=Fraction(1), voters={"carrie"}
    )
    correct_prof = PreferenceProfile(ballots=[abe, don, carrie])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_special_char():
    prof = load_csv(CSV_DIR / "special_char.csv", id_col=0)
    a1 = Ballot(
        ranking=[{"b@#"}, {"@#$"}, {"c"}], weight=Fraction(2), voters={"a@#", "1@#"}
    )
    d = Ballot(ranking=[{"!23"}, {"c"}, {"c"}], weight=Fraction(1), voters={"d#$"})
    correct_prof = PreferenceProfile(ballots=[a1, d])
    assert is_equal(correct_prof.ballots, prof.ballots)


def test_unnamed_ballot():
    with pytest.raises(ValueError):
        load_csv(CSV_DIR / "unnamed.csv", id_col=0)


def test_same_name():
    with pytest.raises(DataError):
        load_csv(CSV_DIR / "same_name.csv", id_col=0)


def test_blt_seats_parse():
    pp, seats = load_blt(BLT_DIR / "edinburgh17-01_abridged.blt")
    assert seats == 4


def test_empty_file_blt():
    with pytest.raises(EmptyDataError):
        pp, seats = load_blt(BLT_DIR / "empty.blt")


def test_bad_metadata_blt():
    with pytest.raises(DataError):
        pp, seats = load_blt(BLT_DIR / "bad_metadata.blt")


def test_incorrect_metadata_blt():
    with pytest.raises(DataError):
        pp, seats = load_blt(BLT_DIR / "candidate_metadata_conflict.blt")
