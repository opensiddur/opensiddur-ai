import unittest
from unittest.mock import MagicMock, patch

import requests

from opensiddur.importer.util import wikisource
from opensiddur.importer.util.wikisource import (
    RateLimiter,
    Wiki,
    WikisourceError,
    api_get,
    batched,
    build_session,
    fetch_contributors,
    fetch_revisions,
    is_bot_name,
    list_book_pages,
    page_title,
    query_pages,
    resolve_contact_email,
)

BOOK = "Some Book.pdf"
NAMESPACE = "עמוד"


def make_response(status_code=200, payload=None, headers=None):
    """A stand-in for requests.Response carrying just what api_get inspects."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload if payload is not None else {}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    else:
        response.raise_for_status.return_value = None
    return response


def make_wiki(*responses):
    """A Wiki whose session returns the given responses in order."""
    session = MagicMock()
    session.get.side_effect = list(responses)
    return Wiki(server="he.wikisource.org", session=session)


def pages_payload(*pages, continuation=None):
    payload = {"query": {"pages": list(pages)}}
    if continuation is not None:
        payload["continue"] = continuation
    else:
        payload["batchcomplete"] = True
    return payload


class TestResolveContactEmail(unittest.TestCase):
    def test_prefers_the_explicit_value(self):
        with patch.dict("os.environ", {wikisource.CONTACT_EMAIL_ENV_VAR: "env@opensiddur.org"}):
            self.assertEqual(resolve_contact_email("cli@opensiddur.org"), "cli@opensiddur.org")

    def test_falls_back_to_the_environment(self):
        with patch.dict("os.environ", {wikisource.CONTACT_EMAIL_ENV_VAR: "env@opensiddur.org"}):
            self.assertEqual(resolve_contact_email(None), "env@opensiddur.org")

    def test_refuses_when_no_address_is_available(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(WikisourceError) as raised:
                resolve_contact_email(None)
        self.assertIn("contact e-mail", str(raised.exception).lower())

    def test_refuses_a_placeholder_domain(self):
        # The whole point of the parameter: never send an address that reaches nobody.
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(WikisourceError):
                resolve_contact_email("opensiddur@example.com")

    def test_refuses_something_that_is_not_an_address(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(WikisourceError):
                resolve_contact_email("not-an-address")


class TestBuildSession(unittest.TestCase):
    def test_identifies_itself_and_requests_compression(self):
        session = build_session("example@opensiddur.org")
        self.assertIn("example@opensiddur.org", session.headers["User-Agent"])
        self.assertIn("opensiddur-ai", session.headers["User-Agent"])
        self.assertIn("gzip", session.headers["Accept-Encoding"])


class TestBatched(unittest.TestCase):
    def test_splits_into_chunks_of_at_most_the_batch_size(self):
        self.assertEqual(list(batched(list(range(5)), 2)), [[0, 1], [2, 3], [4]])

    def test_default_batch_size_matches_the_unauthenticated_titles_limit(self):
        self.assertEqual(len(next(batched(list(range(200))))), 50)

    def test_empty_input_yields_nothing(self):
        self.assertEqual(list(batched([], 10)), [])

    def test_rejects_a_nonsense_batch_size(self):
        with self.assertRaises(ValueError):
            list(batched([1, 2], 0))


class TestPageTitle(unittest.TestCase):
    def test_builds_a_proofread_page_title(self):
        self.assertEqual(page_title(NAMESPACE, BOOK, 50), "עמוד:Some Book.pdf/50")


class TestIsBotName(unittest.TestCase):
    def test_recognises_bots_regardless_of_case(self):
        self.assertTrue(is_bot_name("Wikisource-bot"))
        self.assertTrue(is_bot_name("SomeBot"))

    def test_leaves_ordinary_names_alone(self):
        self.assertFalse(is_bot_name("Dovi"))


class TestApiGet(unittest.TestCase):
    def test_sends_the_required_etiquette_parameters(self):
        wiki = make_wiki(make_response(payload={"query": {}}))
        api_get(wiki, {"action": "query"})

        _, kwargs = wiki.session.get.call_args
        self.assertEqual(kwargs["params"]["format"], "json")
        self.assertEqual(kwargs["params"]["formatversion"], 2)
        self.assertEqual(kwargs["params"]["maxlag"], 5)

    def test_targets_the_action_api(self):
        wiki = make_wiki(make_response(payload={"query": {}}))
        api_get(wiki, {"action": "query"})

        args, _ = wiki.session.get.call_args
        self.assertEqual(args[0], "https://he.wikisource.org/w/api.php")

    def test_waits_and_retries_when_the_database_is_lagging(self):
        # Lag arrives as HTTP 200 with an error in the body, so the status is no help.
        lagging = make_response(
            payload={"error": {"code": "maxlag", "info": "6.2 seconds lagged"}},
            headers={"Retry-After": "6"},
        )
        wiki = make_wiki(lagging, make_response(payload={"query": {"pages": []}}))

        with patch.object(wikisource.time, "sleep") as sleep:
            api_get(wiki, {"action": "query"})

        sleep.assert_called_once_with(6.0)
        self.assertEqual(wiki.session.get.call_count, 2)

    def test_gives_up_on_sustained_lag(self):
        lagging = [
            make_response(payload={"error": {"code": "maxlag", "info": "lagged"}})
            for _ in range(3)
        ]
        wiki = make_wiki(*lagging)

        with patch.object(wikisource.time, "sleep"):
            with self.assertRaises(WikisourceError):
                api_get(wiki, {"action": "query"}, max_retries=2)

    def test_honours_retry_after_on_rate_limiting(self):
        wiki = make_wiki(
            make_response(status_code=429, headers={"Retry-After": "3"}),
            make_response(payload={"query": {"pages": []}}),
        )

        with patch.object(wikisource.time, "sleep") as sleep:
            api_get(wiki, {"action": "query"})

        sleep.assert_called_once_with(3.0)

    def test_backs_off_exponentially_without_retry_after(self):
        wiki = make_wiki(
            make_response(status_code=503),
            make_response(status_code=503),
            make_response(payload={"query": {"pages": []}}),
        )

        with patch.object(wikisource.time, "sleep") as sleep:
            api_get(wiki, {"action": "query"})

        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2.0, 4.0])

    def test_does_not_retry_a_request_that_is_our_own_fault(self):
        wiki = make_wiki(make_response(status_code=400))

        with self.assertRaises(requests.HTTPError):
            api_get(wiki, {"action": "query"})

        self.assertEqual(wiki.session.get.call_count, 1)

    def test_reports_other_api_errors(self):
        wiki = make_wiki(
            make_response(payload={"error": {"code": "badvalue", "info": "nope"}})
        )

        with self.assertRaises(WikisourceError) as raised:
            api_get(wiki, {"action": "query"})

        self.assertIn("badvalue", str(raised.exception))

    def test_paces_requests_when_a_limiter_is_present(self):
        wiki = make_wiki(make_response(payload={"query": {}}))
        wiki.limiter = MagicMock()

        api_get(wiki, {"action": "query"})

        wiki.limiter.wait.assert_called_once()


class TestRateLimiter(unittest.TestCase):
    def test_does_not_delay_the_first_request(self):
        limiter = RateLimiter(min_interval=1.3)
        with patch.object(wikisource.time, "sleep") as sleep:
            limiter.wait()
        sleep.assert_not_called()

    def test_delays_a_request_that_follows_too_closely(self):
        limiter = RateLimiter(min_interval=1.3)
        with patch.object(wikisource.time, "sleep") as sleep:
            with patch.object(wikisource.time, "monotonic", side_effect=[100.0, 100.2]):
                with patch.object(wikisource.random, "random", return_value=0.0):
                    limiter.wait()
                    limiter.wait()
        # 1.3s required, 0.2s elapsed.
        self.assertAlmostEqual(sleep.call_args.args[0], 1.1)

    def test_does_not_delay_once_enough_time_has_passed(self):
        limiter = RateLimiter(min_interval=1.3)
        with patch.object(wikisource.time, "sleep") as sleep:
            with patch.object(wikisource.time, "monotonic", side_effect=[100.0, 110.0]):
                with patch.object(wikisource.random, "random", return_value=0.0):
                    limiter.wait()
                    limiter.wait()
        sleep.assert_not_called()


class TestQueryPages(unittest.TestCase):
    def test_follows_continuation_and_merges_by_title(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {"title": "A", "contributors": [{"name": "One"}]},
                    continuation={"pccontinue": "next"},
                )
            ),
            make_response(
                payload=pages_payload({"title": "A", "contributors": [{"name": "Two"}]})
            ),
        )

        collected = query_pages(wiki, {"action": "query"})

        self.assertEqual(
            [c["name"] for c in collected["A"]["contributors"]], ["One", "Two"]
        )

    def test_passes_the_continuation_token_back(self):
        wiki = make_wiki(
            make_response(payload=pages_payload({"title": "A"}, continuation={"pccontinue": "next"})),
            make_response(payload=pages_payload({"title": "A"})),
        )

        query_pages(wiki, {"action": "query"})

        _, kwargs = wiki.session.get.call_args
        self.assertEqual(kwargs["params"]["pccontinue"], "next")

    def test_drops_pages_the_wiki_does_not_have(self):
        wiki = make_wiki(
            make_response(payload=pages_payload({"title": "Gone", "missing": True}, {"title": "Here"}))
        )

        self.assertEqual(list(query_pages(wiki, {"action": "query"})), ["Here"])


class TestListBookPages(unittest.TestCase):
    def test_collects_page_numbers_across_continuation(self):
        # The API orders titles lexicographically (/1, /10, /100), so any numeric
        # reading of a single batch looks full of gaps that are not real.
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {"title": f"{NAMESPACE}:{BOOK}/1"},
                    {"title": f"{NAMESPACE}:{BOOK}/10"},
                    {"title": f"{NAMESPACE}:{BOOK}/100"},
                    continuation={"gapcontinue": f"{BOOK}/2"},
                )
            ),
            make_response(
                payload=pages_payload(
                    {"title": f"{NAMESPACE}:{BOOK}/2"},
                    {"title": f"{NAMESPACE}:{BOOK}/3"},
                )
            ),
        )

        found = list_book_pages(wiki, BOOK)

        self.assertEqual(sorted(found), [1, 2, 3, 10, 100])
        self.assertEqual(found[100], f"{NAMESPACE}:{BOOK}/100")

    def test_ignores_subpages_that_are_not_numbered_scan_pages(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {"title": f"{NAMESPACE}:{BOOK}/7"},
                    {"title": f"{NAMESPACE}:{BOOK}/7/notes"},
                    {"title": f"{NAMESPACE}:{BOOK}/appendix"},
                )
            )
        )

        self.assertEqual(sorted(list_book_pages(wiki, BOOK)), [7])

    def test_asks_for_the_proofread_page_namespace(self):
        wiki = make_wiki(make_response(payload=pages_payload()))

        list_book_pages(wiki, BOOK)

        _, kwargs = wiki.session.get.call_args
        self.assertEqual(kwargs["params"]["gapnamespace"], 104)
        self.assertEqual(kwargs["params"]["gapprefix"], f"{BOOK}/")


class TestFetchRevisions(unittest.TestCase):
    def test_reads_revision_ids_without_asking_for_wikitext(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {
                        "title": f"{NAMESPACE}:{BOOK}/1",
                        "revisions": [{"revid": 111, "timestamp": "2021-01-01T00:00:00Z"}],
                    },
                    {
                        "title": f"{NAMESPACE}:{BOOK}/2",
                        "revisions": [{"revid": 222, "timestamp": "2021-01-02T00:00:00Z"}],
                    },
                )
            )
        )

        found = fetch_revisions(
            wiki, [f"{NAMESPACE}:{BOOK}/1", f"{NAMESPACE}:{BOOK}/2"], include_content=False
        )

        self.assertEqual(found[f"{NAMESPACE}:{BOOK}/1"].revid, 111)
        self.assertIsNone(found[f"{NAMESPACE}:{BOOK}/2"].content)

        _, kwargs = wiki.session.get.call_args
        self.assertNotIn("content", kwargs["params"]["rvprop"])
        self.assertNotIn("rvslots", kwargs["params"])

    def test_reads_wikitext_when_asked(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {
                        "title": f"{NAMESPACE}:{BOOK}/1",
                        "revisions": [
                            {
                                "revid": 111,
                                "timestamp": "2021-01-01T00:00:00Z",
                                "user": "Dovi",
                                "slots": {"main": {"content": "שלום"}},
                            }
                        ],
                    }
                )
            )
        )

        found = fetch_revisions(wiki, [f"{NAMESPACE}:{BOOK}/1"], include_content=True)

        self.assertEqual(found[f"{NAMESPACE}:{BOOK}/1"].content, "שלום")
        self.assertEqual(found[f"{NAMESPACE}:{BOOK}/1"].user, "Dovi")

        _, kwargs = wiki.session.get.call_args
        self.assertIn("content", kwargs["params"]["rvprop"])
        self.assertEqual(kwargs["params"]["rvslots"], "main")

    def test_batches_titles_to_stay_within_the_api_limit(self):
        titles = [f"{NAMESPACE}:{BOOK}/{n}" for n in range(1, 121)]
        wiki = make_wiki(*[make_response(payload=pages_payload()) for _ in range(3)])

        fetch_revisions(wiki, titles, include_content=False)

        self.assertEqual(wiki.session.get.call_count, 3)

    def test_skips_pages_with_no_revisions(self):
        wiki = make_wiki(
            make_response(payload=pages_payload({"title": f"{NAMESPACE}:{BOOK}/1"}))
        )

        self.assertEqual(fetch_revisions(wiki, [f"{NAMESPACE}:{BOOK}/1"], include_content=False), {})


class TestFetchContributors(unittest.TestCase):
    def test_returns_named_accounts_sorted_and_without_bots(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {
                        "title": f"{NAMESPACE}:{BOOK}/50",
                        "contributors": [
                            {"userid": 68, "name": "Nahum"},
                            {"userid": 1, "name": "Dovi"},
                            {"userid": 9, "name": "Wikisource-bot"},
                        ],
                    }
                )
            )
        )

        found = fetch_contributors(wiki, [f"{NAMESPACE}:{BOOK}/50"])

        self.assertEqual(found[f"{NAMESPACE}:{BOOK}/50"], ["Dovi", "Nahum"])

    def test_deduplicates_names(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {
                        "title": f"{NAMESPACE}:{BOOK}/50",
                        "contributors": [{"name": "Dovi"}, {"name": "Dovi"}],
                    }
                )
            )
        )

        self.assertEqual(
            fetch_contributors(wiki, [f"{NAMESPACE}:{BOOK}/50"])[f"{NAMESPACE}:{BOOK}/50"],
            ["Dovi"],
        )

    def test_honours_a_custom_exclusion(self):
        wiki = make_wiki(
            make_response(
                payload=pages_payload(
                    {
                        "title": f"{NAMESPACE}:{BOOK}/50",
                        "contributors": [{"name": "Dovi"}, {"name": "Nahum"}],
                    }
                )
            )
        )

        found = fetch_contributors(
            wiki, [f"{NAMESPACE}:{BOOK}/50"], exclude=lambda name: name == "Nahum"
        )

        self.assertEqual(found[f"{NAMESPACE}:{BOOK}/50"], ["Dovi"])


if __name__ == "__main__":
    unittest.main()
