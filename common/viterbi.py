"""Viterbi: the cheapest path through a sequence of steps, each with its own options.

The decoding step of an HMM (Rabiner 1989, "A tutorial on hidden Markov models
and selected applications in speech recognition", Proc. IEEE 77(2), sec. III-B,
not yet read here, so cited as unverified), written with costs (negative log
probabilities) instead of probabilities, so it adds instead of multiplying:

    total = sum over steps t of unary(t, option chosen at t)
          + sum over consecutive steps of pair(option at t-1, option at t)

Used by the simplification (simplification/simplify.py) and, as
docs/next_steps.md plans, for any decoding with a change penalty.
"""


def decode(unary, pair):
    """(the cheapest path as option indices, its total cost).

    unary: for each step, a list of costs, one per option at that step.
    pair(t, i, j): the cost of option i at step t - 1 followed by option j at step t.
    """
    if not unary:
        return [], 0.0
    cost = list(unary[0])
    back = []
    for t in range(1, len(unary)):
        here, ptr = [], []
        for j, u in enumerate(unary[t]):
            best_i = min(range(len(cost)), key=lambda i: cost[i] + pair(t, i, j))
            here.append(cost[best_i] + pair(t, best_i, j) + u)
            ptr.append(best_i)
        cost, back = here, back + [ptr]
    j = min(range(len(cost)), key=lambda i: cost[i])
    total, path = cost[j], [j]
    for ptr in reversed(back):
        j = ptr[j]
        path.append(j)
    return path[::-1], total
