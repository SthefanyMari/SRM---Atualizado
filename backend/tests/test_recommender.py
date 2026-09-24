from types import SimpleNamespace

from app.services.recommender import rank_contents


def test_preferred_domain_ranks_first():
    movie = SimpleNamespace(id=1, title="Filme", domain="filme", category="Drama")
    book = SimpleNamespace(id=2, title="Livro", domain="livro", category="Fantasia")
    preference = SimpleNamespace(
        profile={"preferred_domains": ["livro"], "preferred_categories": []}
    )

    ranked = rank_contents([movie, book], preference, [])

    assert ranked[0][0].id == 2
    assert ranked[0][1] > ranked[1][1]
