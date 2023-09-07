import itertools as it
import math
import pytest
import scipy.stats as stats
from pathlib import Path
import pickle
import numpy as np

from votekit.ballot_generator import (
    ImpartialAnonymousCulture,
    ImpartialCulture,
    PlackettLuce,
    BradleyTerry,
    AlternatingCrossover,
    CambridgeSampler,
    OneDimSpatial,
    BallotSimplex,
)
from votekit.metrics.distances import lp_dist
from votekit.pref_profile import PreferenceProfile

# set seed for more consistent tests
np.random.seed(8675309)


def test_IC_completion():
    ic = ImpartialCulture(candidates=["W1", "W2", "C1", "C2"], ballot_length=None)
    profile = ic.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_IAC_completion():
    iac = ImpartialAnonymousCulture(
        candidates=["W1", "W2", "C1", "C2"], ballot_length=None
    )
    profile = iac.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_PL_completion():
    pl = PlackettLuce(
        candidates=["W1", "W2", "C1", "C2"],
        ballot_length=None,
        pref_interval_by_bloc={
            "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
            "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
        },
        bloc_voter_prop={"W": 0.7, "C": 0.3},
    )
    profile = pl.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_BT_completion():
    bt = BradleyTerry(
        candidates=["W1", "W2", "C1", "C2"],
        ballot_length=None,
        pref_interval_by_bloc={
            "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
            "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
        },
        bloc_voter_prop={"W": 0.7, "C": 0.3},
    )
    profile = bt.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_AC_completion():
    ac = AlternatingCrossover(
        candidates=["W1", "W2", "C1", "C2"],
        ballot_length=None,
        slate_to_candidates={"W": ["W1", "W2"], "C": ["C1", "C2"]},
        pref_interval_by_bloc={
            "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
            "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
        },
        bloc_voter_prop={"W": 0.7, "C": 0.3},
        bloc_crossover_rate={"W": {"C": 0.3}, "C": {"W": 0.1}},
    )
    profile = ac.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_1D_completion():
    ods = OneDimSpatial(candidates=["W1", "W2", "C1", "C2"], ballot_length=None)
    profile = ods.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def test_Cambridge_completion():

    cs = CambridgeSampler(
        candidates=["W1", "W2", "C1", "C2"],
        ballot_length=None,
        slate_to_candidates={"W": ["W1", "W2"], "C": ["C1", "C2"]},
        pref_interval_by_bloc={
            "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
            "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
        },
        bloc_voter_prop={"W": 0.7, "C": 0.3},
        bloc_crossover_rate={"W": {"C": 0.3}, "C": {"W": 0.1}},
    )
    profile = cs.generate_profile(number_of_ballots=100)
    assert type(profile) is PreferenceProfile


def binomial_confidence_interval(probability, n_attempts, alpha=0.95):
    # Calculate the mean and standard deviation of the binomial distribution
    mean = n_attempts * probability
    std_dev = math.sqrt(n_attempts * probability * (1 - probability))

    # Calculate the confidence interval
    z_score = stats.norm.ppf((1 + alpha) / 2)  # Z-score for 99% confidence level
    margin_of_error = z_score * (std_dev)
    conf_interval = (mean - margin_of_error, mean + margin_of_error)

    return conf_interval


def do_ballot_probs_match_ballot_dist(
    ballot_prob_dict: dict, generated_profile: PreferenceProfile, n: int, alpha=0.95
):

    n_ballots = generated_profile.num_ballots()
    ballot_conf_dict = {
        b: binomial_confidence_interval(p, n_attempts=int(n_ballots), alpha=alpha)
        for b, p in ballot_prob_dict.items()
    }

    failed = 0

    for b in ballot_conf_dict.keys():
        b_list = [{c} for c in b]
        ballot = next(
            (
                element
                for element in generated_profile.ballots
                if element.ranking == b_list
            ),
            None,
        )
        ballot_weight = 0
        if ballot is not None:
            ballot_weight = ballot.weight
        if not (
            int(ballot_conf_dict[b][0]) <= ballot_weight <= int(ballot_conf_dict[b][1])
        ):
            failed += 1

    # allow for small margin of error given confidence intereval
    failure_thresold = 5
    return failed <= failure_thresold


def test_ic_distribution():
    # Set-up
    number_of_ballots = 100
    ballot_length = 4
    candidates = ["W1", "W2", "C1", "C2"]

    # Find ballot probs
    possible_rankings = it.permutations(candidates, ballot_length)
    ballot_prob_dict = {
        b: 1 / math.factorial(len(candidates)) for b in possible_rankings
    }

    # Generate ballots
    generated_profile = ImpartialCulture(
        ballot_length=ballot_length,
        candidates=candidates,
    ).generate_profile(number_of_ballots=number_of_ballots)

    # Test
    assert do_ballot_probs_match_ballot_dist(
        ballot_prob_dict, generated_profile, len(candidates)
    )


def test_ballot_simplex_from_point():
    number_of_ballots = 1000
    ballot_length = 4
    candidates = ["W1", "W2", "C1", "C2"]
    pt = {"W1": 1 / 4, "W2": 1 / 4, "C1": 1 / 4, "C2": 1 / 4}

    possible_rankings = it.permutations(candidates, ballot_length)
    ballot_prob_dict = {
        b: 1 / math.factorial(len(candidates)) for b in possible_rankings
    }

    generated_profile = BallotSimplex.from_point(
        point=pt, ballot_length=ballot_length, candidates=candidates
    ).generate_profile(number_of_ballots=number_of_ballots)
    # Test
    assert do_ballot_probs_match_ballot_dist(
        ballot_prob_dict, generated_profile, len(candidates)
    )


def test_ballot_simplex_from_alpha_zero():
    number_of_ballots = 1000
    candidates = ["W1", "W2", "C1", "C2"]

    generated_profile = BallotSimplex.from_alpha(
        alpha=0, candidates=candidates
    ).generate_profile(number_of_ballots=number_of_ballots)

    assert len(generated_profile.ballots) == 1


# def test_iac_distribution():
#     number_of_ballots = 1000
#     ballot_length = 4
#     candidates = ["W1", "W2", "C1", "C2"]

#     # Find ballot probs
#     possible_rankings = list(it.permutations(candidates, ballot_length))
#     probabilities = np.random.dirichlet([1] * len(possible_rankings))

#     ballot_prob_dict = {
#         possible_rankings[b_ind]: probabilities[b_ind]
#         for b_ind in range(len(possible_rankings))
#     }
#     generated_profile = IAC(
#         number_of_ballots=number_of_ballots,
#         ballot_length=ballot_length,
#         candidates=candidates,
#     ).generate_profile()

#     # Test
#     assert do_ballot_probs_match_ballot_dist(ballot_prob_dict, generated_profile)


def slow_PL(candidates, bloc_voter_prop, pref_interval_by_bloc, number_of_ballots):
    ballot_pool = []
    ballot_length = len(candidates)

    for bloc in bloc_voter_prop.keys():
        # number of voters in this bloc
        num_ballots = PlackettLuce.round_num(number_of_ballots * bloc_voter_prop[bloc])
        pref_interval_dict = pref_interval_by_bloc[bloc]
        # creates the interval of probabilities for candidates supported by this block
        cand_support_vec = [pref_interval_dict[cand] for cand in candidates]

        for _ in range(num_ballots):
            # generates ranking based on probability distribution of candidate support
            ballot = list(
                np.random.choice(
                    candidates,
                    ballot_length,
                    p=cand_support_vec,
                    replace=False,
                )
            )

            ballot_pool.append(ballot)

    pp = PlackettLuce.ballot_pool_to_profile(
        ballot_pool=ballot_pool, candidates=candidates
    )
    return pp


def test_PL_distribution():
    # Set-up
    number_of_ballots = 100
    candidates = ["W1", "W2", "C1", "C2"]
    ballot_length = None
    pref_interval_by_bloc = {
        "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
        "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
    }
    bloc_voter_prop = {"W": 0.7, "C": 0.3}

    # Generate ballots
    generated_profile = PlackettLuce(
        ballot_length=ballot_length,
        candidates=candidates,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
    ).generate_profile(number_of_ballots=number_of_ballots)

    mock_profile = slow_PL(
        candidates=candidates,
        bloc_voter_prop=bloc_voter_prop,
        pref_interval_by_bloc=pref_interval_by_bloc,
        number_of_ballots=number_of_ballots,
    )

    # what's a good threshold for l1 distance?
    print(lp_dist(generated_profile, mock_profile))
    assert False


def test_BT_distribution():

    # Set-up
    number_of_ballots = 100
    ballot_length = 4
    candidates = ["W1", "W2", "C1", "C2"]
    ballot_length = None
    pref_interval_by_bloc = {
        "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
        "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
    }
    bloc_voter_prop = {"W": 0.7, "C": 0.3}

    # Find ballot probs
    possible_rankings = list(it.permutations(candidates, ballot_length))

    final_ballot_prob_dict = {b: 0 for b in possible_rankings}

    for bloc in bloc_voter_prop.keys():
        ballot_prob_dict = {b: 0 for b in possible_rankings}
        for ranking in possible_rankings:
            support_for_cands = pref_interval_by_bloc[bloc]
            prob = bloc_voter_prop[bloc]
            for i in range(len(ranking)):
                greater_cand = support_for_cands[ranking[i]]
                for j in range(i + 1, len(ranking)):
                    cand = support_for_cands[ranking[j]]
                    prob *= greater_cand / (greater_cand + cand)
            ballot_prob_dict[ranking] += prob
        normalizer = 1 / sum(ballot_prob_dict.values())
        ballot_prob_dict = {k: v * normalizer for k, v in ballot_prob_dict.items()}
        final_ballot_prob_dict = {
            k: v + bloc_voter_prop[bloc] * ballot_prob_dict[k]
            for k, v in final_ballot_prob_dict.items()
        }

    # Generate ballots
    generated_profile = BradleyTerry(
        ballot_length=ballot_length,
        candidates=candidates,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
    ).generate_profile(number_of_ballots=number_of_ballots)

    # Test
    assert do_ballot_probs_match_ballot_dist(
        final_ballot_prob_dict, generated_profile, len(candidates)
    )


def test_BT_probability_calculation():

    # Set-up
    ballot_length = 4
    candidates = ["W1", "W2", "C1", "C2"]
    ballot_length = None
    pref_interval_by_bloc = {
        "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
        "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
    }
    bloc_voter_prop = {"W": 0.7, "C": 0.3}

    model = BradleyTerry(
        ballot_length=ballot_length,
        candidates=candidates,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
    )

    permutation = ("W1", "W2")

    w_pref_interval = pref_interval_by_bloc["W"]
    c_pref_interval = pref_interval_by_bloc["C"]

    assert model.calculate_ranking_probs(
        permutations=[permutation], cand_support_dict=pref_interval_by_bloc["C"]
    )[permutation] == (
        c_pref_interval["W1"] / (c_pref_interval["W1"] + c_pref_interval["W2"])
    )

    permutation = ("W1", "W2", "C2")
    prob = (
        (w_pref_interval["W1"] / (w_pref_interval["W1"] + w_pref_interval["W2"]))
        * (w_pref_interval["W1"] / (w_pref_interval["W1"] + w_pref_interval["C2"]))
        * (w_pref_interval["W2"] / (w_pref_interval["W2"] + w_pref_interval["C2"]))
    )
    assert (
        model.calculate_ranking_probs(
            permutations=[permutation], cand_support_dict=pref_interval_by_bloc["W"]
        )[permutation]
        == prob
    )


def slow_AC(
    candidates,
    bloc_voter_prop,
    slate_to_candidates,
    pref_interval_by_bloc,
    bloc_crossover_rate,
):
    ballot_pool = []
    number_of_ballots = len(candidates)

    for bloc in bloc_voter_prop.keys():

        num_ballots = AlternatingCrossover.round_num(
            number_of_ballots * bloc_voter_prop[bloc]
        )
        crossover_dict = bloc_crossover_rate[bloc]
        pref_interval_dict = pref_interval_by_bloc[bloc]

        # generates crossover ballots from each bloc (allowing for more than two blocs)
        for opposing_slate in crossover_dict.keys():
            crossover_rate = crossover_dict[opposing_slate]
            num_crossover_ballots = AlternatingCrossover.round_num(
                crossover_rate * num_ballots
            )

            opposing_cands = slate_to_candidates[opposing_slate]
            bloc_cands = slate_to_candidates[bloc]

            for _ in range(num_crossover_ballots):
                pref_for_opposing = [
                    pref_interval_dict[cand] for cand in opposing_cands
                ]
                # convert to probability distribution
                pref_for_opposing = [
                    p / sum(pref_for_opposing) for p in pref_for_opposing
                ]

                pref_for_bloc = [pref_interval_dict[cand] for cand in bloc_cands]
                # convert to probability distribution
                pref_for_bloc = [p / sum(pref_for_bloc) for p in pref_for_bloc]

                bloc_cands = list(
                    np.random.choice(
                        bloc_cands,
                        p=pref_for_bloc,
                        size=len(bloc_cands),
                        replace=False,
                    )
                )
                opposing_cands = list(
                    np.random.choice(
                        opposing_cands,
                        size=len(opposing_cands),
                        p=pref_for_opposing,
                        replace=False,
                    )
                )

                # alternate the bloc and opposing bloc candidates to create crossover ballots
                if bloc != opposing_slate:  # alternate
                    ballot = [
                        item
                        for pair in zip(opposing_cands, bloc_cands)
                        for item in pair
                        if item is not None
                    ]

                # check that ballot_length is shorter than total number of cands
                ballot_pool.append(ballot)

            # Bloc ballots
            for _ in range(num_ballots - num_crossover_ballots):
                ballot = bloc_cands + opposing_cands
                ballot_pool.append(ballot)

    pp = AlternatingCrossover.ballot_pool_to_profile(
        ballot_pool=ballot_pool, candidates=candidates
    )
    return pp


def test_AC_distribution():

    # Set-up
    number_of_ballots = 1000
    ballot_length = 4
    candidates = ["W1", "W2", "C1", "C2"]
    ballot_length = None
    slate_to_candidate = {"W": ["W1", "W2"], "C": ["C1", "C2"]}

    pref_interval_by_bloc = {
        "W": {"W1": 0.4, "W2": 0.3, "C1": 0.2, "C2": 0.1},
        "C": {"W1": 0.2, "W2": 0.2, "C1": 0.3, "C2": 0.3},
    }
    bloc_voter_prop = {"W": 0.7, "C": 0.3}
    bloc_crossover_rate = {"W": {"C": 1}, "C": {"W": 1}}

    # Generate ballots
    generated_profile = AlternatingCrossover(
        ballot_length=ballot_length,
        candidates=candidates,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
        slate_to_candidates=slate_to_candidate,
        bloc_crossover_rate=bloc_crossover_rate,
    ).generate_profile(number_of_ballots)

    mock_profile = slow_AC(
        candidates=candidates,
        bloc_crossover_rate=bloc_crossover_rate,
        slate_to_candidates=slate_to_candidate,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
    )

    print(lp_dist(generated_profile, mock_profile))
    assert False


def compute_pl_prob(perm, interval):
    pref_interval = interval.copy()
    prob = 1
    for c in perm:
        if sum(pref_interval.values()) == 0:
            prob *= 1 / math.factorial(len(pref_interval))
        else:
            prob *= pref_interval[c] / sum(pref_interval.values())
        del pref_interval[c]
    return prob


def bloc_order_probs_slate_first(slate, ballot_frequencies):
    slate_first_count = sum(
        [freq for ballot, freq in ballot_frequencies.items() if ballot[0] == slate]
    )
    prob_ballot_given_slate_first = {
        ballot: freq / slate_first_count
        for ballot, freq in ballot_frequencies.items()
        if ballot[0] == slate
    }
    return prob_ballot_given_slate_first


def test_setparams_pl():
    blocs = {"R": 0.6, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}

    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    pl = PlackettLuce.from_params(
        slate_to_candidates=slate_to_cands,
        bloc_voter_prop=blocs,
        cohesion=cohesion,
        alphas=alphas,
    )
    # check params were set
    assert pl.bloc_voter_prop == {"R": 0.6, "D": 0.4}
    interval = pl.pref_interval_by_bloc
    # check if intervals add up to one
    assert math.isclose(sum(interval["R"].values()), 1)
    assert math.isclose(sum(interval["D"].values()), 1)


def test_bt_single_bloc():
    blocs = {"R": 0.6, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    gen = BradleyTerry.from_params(
        slate_to_candidates=slate_to_cands,
        bloc_voter_prop=blocs,
        cohesion=cohesion,
        alphas=alphas,
    )
    interval = gen.pref_interval_by_bloc
    assert math.isclose(sum(interval["R"].values()), 1)


def test_incorrect_blocs():
    blocs = {"R": 0.7, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    with pytest.raises(ValueError):
        PlackettLuce.from_params(
            slate_to_candidates=slate_to_cands,
            bloc_voter_prop=blocs,
            cohesion=cohesion,
            alphas=alphas,
        )


def test_ac_profile_from_params():
    blocs = {"R": 0.6, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}
    crossover = {"R": {"D": 0.5}, "D": {"R": 0.6}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}
    ac = AlternatingCrossover.from_params(
        bloc_voter_prop=blocs,
        cohesion=cohesion,
        alphas=alphas,
        slate_to_candidates=slate_to_cands,
        bloc_crossover_rate=crossover,
    )

    profile = ac.generate_profile(3)
    assert type(profile) is PreferenceProfile


def test_pl_profile_from_params():
    blocs = {"R": 0.6, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    ac = PlackettLuce.from_params(
        bloc_voter_prop=blocs,
        slate_to_candidates=slate_to_cands,
        cohesion=cohesion,
        alphas=alphas,
    )

    profile = ac.generate_profile(3)
    assert type(profile) is PreferenceProfile


def test_interval_sum_from_params():

    blocs = {"R": 0.6, "D": 0.4}
    cohesion = {"R": 0.7, "D": 0.6}
    alphas = {"R": {"R": 0.5, "D": 1}, "D": {"R": 1, "D": 0.5}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    ac = PlackettLuce.from_params(
        bloc_voter_prop=blocs,
        slate_to_candidates=slate_to_cands,
        cohesion=cohesion,
        alphas=alphas,
    )
    for b in ac.pref_interval_by_bloc:
        if not math.isclose(sum(ac.pref_interval_by_bloc[b].values()), 1):
            assert False
    assert True


def test_interval_from_params():

    blocs = {"R": 0.9, "D": 0.1}
    cohesion = {"R": 0.9, "D": 0.9}
    alphas = {"R": {"R": 1, "D": 1}, "D": {"R": 1, "D": 1}}
    slate_to_cands = {"R": ["A1", "B1", "C1"], "D": ["A2", "B2"]}

    ac = PlackettLuce.from_params(
        bloc_voter_prop=blocs,
        slate_to_candidates=slate_to_cands,
        cohesion=cohesion,
        alphas=alphas,
    )

    for b in blocs:
        pref = ac.pref_interval_by_bloc[b].values()
        if not any(value > 0.4 for value in pref):
            assert False

    assert True


def test_Cambridge_distribution():
    # BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = "src/votekit/data"
    path = Path(DATA_DIR, "Cambridge_09to17_ballot_types.p")

    candidates = ["W1", "W2", "C1", "C2"]
    ballot_length = None
    slate_to_candidate = {"W": ["W1", "W2"], "C": ["C1", "C2"]}
    pref_interval_by_bloc = {
        "W": {"W1": 0.4, "W2": 0.4, "C1": 0.1, "C2": 0.1},
        "C": {"W1": 0.1, "W2": 0.1, "C1": 0.4, "C2": 0.4},
    }
    bloc_voter_prop = {"W": 0.5, "C": 0.5}
    bloc_crossover_rate = {"W": {"C": 0}, "C": {"W": 0}}

    cs = CambridgeSampler(
        candidates=candidates,
        ballot_length=ballot_length,
        slate_to_candidates=slate_to_candidate,
        pref_interval_by_bloc=pref_interval_by_bloc,
        bloc_voter_prop=bloc_voter_prop,
        bloc_crossover_rate=bloc_crossover_rate,
        path=path,
    )

    with open(path, "rb") as pickle_file:
        ballot_frequencies = pickle.load(pickle_file)
    slates = list(slate_to_candidate.keys())

    # Let's update the running probability of the ballot based on where we are in the nesting
    ballot_prob_dict = dict()
    ballot_prob = [0, 0, 0, 0, 0]
    # p(white) vs p(poc)
    for slate in slates:
        opp_slate = next(iter(set(slates).difference(set(slate))))

        slate_cands = slate_to_candidate[slate]
        opp_cands = slate_to_candidate[opp_slate]

        ballot_prob[0] = bloc_voter_prop[slate]
        prob_ballot_given_slate_first = bloc_order_probs_slate_first(
            slate, ballot_frequencies
        )
        # p(crossover) vs p(non-crossover)
        for voter_bloc in slates:
            opp_voter_bloc = next(iter(set(slates).difference(set(voter_bloc))))
            if voter_bloc == slate:
                ballot_prob[1] = 1 - bloc_crossover_rate[voter_bloc][opp_voter_bloc]

                # p(bloc ordering)
                for (
                    slate_first_ballot,
                    slate_ballot_prob,
                ) in prob_ballot_given_slate_first.items():
                    ballot_prob[2] = slate_ballot_prob

                    # Count number of each slate in the ballot
                    slate_ballot_count_dict = {}
                    for s, sc in slate_to_candidate.items():
                        count = sum([c == s for c in slate_first_ballot])
                        slate_ballot_count_dict[s] = min(count, len(sc))

                    # Make all possible perms with right number of slate candidates
                    slate_perms = list(
                        set(
                            [
                                p[: slate_ballot_count_dict[slate]]
                                for p in list(it.permutations(slate_cands))
                            ]
                        )
                    )
                    opp_perms = list(
                        set(
                            [
                                p[: slate_ballot_count_dict[opp_slate]]
                                for p in list(it.permutations(opp_cands))
                            ]
                        )
                    )

                    only_slate_interval = {
                        c: share
                        for c, share in pref_interval_by_bloc[voter_bloc].items()
                        if c in slate_cands
                    }
                    only_opp_interval = {
                        c: share
                        for c, share in pref_interval_by_bloc[voter_bloc].items()
                        if c in opp_cands
                    }
                    for sp in slate_perms:
                        ballot_prob[3] = compute_pl_prob(sp, only_slate_interval)
                        for op in opp_perms:
                            ballot_prob[4] = compute_pl_prob(op, only_opp_interval)

                            # ADD PROB MULT TO DICT
                            ordered_slate_cands = list(sp)
                            ordered_opp_cands = list(op)
                            ballot_ranking = []
                            for c in slate_first_ballot:
                                if c == slate:
                                    if ordered_slate_cands:
                                        ballot_ranking.append(
                                            ordered_slate_cands.pop(0)
                                        )
                                else:
                                    if ordered_opp_cands:
                                        ballot_ranking.append(ordered_opp_cands.pop(0))
                            prob = np.prod(ballot_prob)
                            ballot = tuple(ballot_ranking)
                            ballot_prob_dict[ballot] = (
                                ballot_prob_dict.get(ballot, 0) + prob
                            )
            else:
                ballot_prob[1] = bloc_crossover_rate[voter_bloc][opp_voter_bloc]

                # p(bloc ordering)
                for (
                    slate_first_ballot,
                    slate_ballot_prob,
                ) in prob_ballot_given_slate_first.items():
                    ballot_prob[2] = slate_ballot_prob

                    # Count number of each slate in the ballot
                    slate_ballot_count_dict = {}
                    for s, sc in slate_to_candidate.items():
                        count = sum([c == s for c in slate_first_ballot])
                        slate_ballot_count_dict[s] = min(count, len(sc))

                    # Make all possible perms with right number of slate candidates
                    slate_perms = [
                        p[: slate_ballot_count_dict[slate]]
                        for p in list(it.permutations(slate_cands))
                    ]
                    opp_perms = [
                        p[: slate_ballot_count_dict[opp_slate]]
                        for p in list(it.permutations(opp_cands))
                    ]
                    only_slate_interval = {
                        c: share
                        for c, share in pref_interval_by_bloc[opp_voter_bloc].items()
                        if c in slate_cands
                    }
                    only_opp_interval = {
                        c: share
                        for c, share in pref_interval_by_bloc[opp_voter_bloc].items()
                        if c in opp_cands
                    }
                    for sp in slate_perms:
                        ballot_prob[3] = compute_pl_prob(sp, only_slate_interval)
                        for op in opp_perms:
                            ballot_prob[4] = compute_pl_prob(op, only_opp_interval)

                            # ADD PROB MULT TO DICT
                            ordered_slate_cands = list(sp)
                            ordered_opp_cands = list(op)
                            ballot_ranking = []
                            for c in slate_first_ballot:
                                if c == slate:
                                    if ordered_slate_cands:
                                        ballot_ranking.append(ordered_slate_cands.pop())
                                else:
                                    if ordered_opp_cands:
                                        ballot_ranking.append(ordered_opp_cands.pop())
                            prob = np.prod(ballot_prob)
                            ballot = tuple(ballot_ranking)
                            ballot_prob_dict[ballot] = (
                                ballot_prob_dict.get(ballot, 0) + prob
                            )

    # Now see if ballot prob dict is right
    test_profile = cs.generate_profile(number_of_ballots=5000)
    assert do_ballot_probs_match_ballot_dist(
        ballot_prob_dict=ballot_prob_dict,
        generated_profile=test_profile,
        n=len(candidates),
    )
