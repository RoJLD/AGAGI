from tools.grad_mem import train_mutation


def test_train_mutation_deterministic():
    # memes args + meme seed -> accuracy identique (reproductible).
    a = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=50, seed=7)
    b = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=50, seed=7)
    assert a == b


def test_train_mutation_returns_valid_accuracy():
    a = train_mutation(N=10, I=8, O=8, K=1, D=0, epochs=20, seed=1)
    assert 0.0 <= a <= 1.0


def test_train_mutation_learns_trivial_recall():
    # 1 bit, sans delai (D=0), budget genereux -> doit depasser le hasard (0.5) nettement.
    a = train_mutation(N=12, I=8, O=8, K=1, D=0, epochs=600, seed=3)
    assert a >= 0.7, f"mutation doit apprendre le rappel 1-bit sans delai (acc={a})"
