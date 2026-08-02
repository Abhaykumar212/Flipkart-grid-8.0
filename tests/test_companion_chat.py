"""Tests for the companion chat agent: prompt assembly and context grounding.

Mirrors test_rca_agent.py's philosophy — no live Groq call here (network
behaviour is a separate concern); what matters is that the prompt is built
correctly and stays grounded in exactly the context supplied.
"""

import unittest

from backend.agents import companion_chat
from backend.schemas import (
    ChatMessage,
    ProductContext,
    ProductReview,
    ProductSpecItem,
    RatingDistributionEntry,
)


def sample_product(**overrides) -> ProductContext:
    base = dict(
        title="Apple iPhone 16 (Ultramarine, 128 GB)",
        brand="Apple",
        category="mobiles",
        mrp=79900,
        selling_price=71999,
        description="A capable daily driver with a great camera.",
        highlights=["128 GB ROM", "6.1 inch display"],
        specifications=[ProductSpecItem(label="RAM", value="6 GB")],
        delivery_free=True,
        estimated_delivery_days=1,
        emi_monthly=2521,
        emi_months=36,
        offers=["Flat ₹4,000 off on HDFC cards"],
        seller_name="Apple Retail India",
        seller_rating=4.8,
        rating_value=4.6,
        rating_count=100,
        rating_distribution=[
            RatingDistributionEntry(stars=5, count=68),
            RatingDistributionEntry(stars=4, count=20),
            RatingDistributionEntry(stars=3, count=7),
            RatingDistributionEntry(stars=2, count=3),
            RatingDistributionEntry(stars=1, count=2),
        ],
        in_stock=True,
        quantity_left=18,
        reviews=[
            ProductReview(rating=5, title="Great phone", text="Battery lasts all day."),
            ProductReview(rating=2, title="Warm to the touch", text="Gets hot during gaming."),
        ],
    )
    base.update(overrides)
    return ProductContext(**base)


class ProductBlockTests(unittest.TestCase):
    def test_includes_price_and_delivery(self):
        block = companion_chat.build_product_block(sample_product())
        self.assertIn("71,999", block)
        self.assertIn("79,900", block)
        self.assertIn("Free", block)

    def test_includes_emi_when_present(self):
        block = companion_chat.build_product_block(sample_product())
        self.assertIn("2521", block.replace(",", ""))
        self.assertIn("36 months", block)

    def test_omits_emi_when_absent(self):
        block = companion_chat.build_product_block(sample_product(emi_monthly=None, emi_months=None))
        self.assertIn("No EMI option listed", block)

    def test_includes_both_positive_and_negative_reviews(self):
        block = companion_chat.build_product_block(sample_product())
        self.assertIn("Great phone", block)
        self.assertIn("Warm to the touch", block)

    def test_handles_no_reviews_honestly(self):
        block = companion_chat.build_product_block(sample_product(reviews=[]))
        self.assertIn("No reviews available", block)

    def test_includes_specifications(self):
        block = companion_chat.build_product_block(sample_product())
        self.assertIn("RAM: 6 GB", block)

    def test_rating_distribution_includes_exact_percentages(self):
        block = companion_chat.build_product_block(sample_product())
        self.assertIn("5★: 68 ratings (68%)", block)
        self.assertIn("88% of all ratings are 4★ or 5★", block)

    def test_stock_shown_with_quantity(self):
        block = companion_chat.build_product_block(sample_product(in_stock=True, quantity_left=18))
        self.assertIn("In stock (18 left)", block)

    def test_out_of_stock_is_stated_plainly(self):
        block = companion_chat.build_product_block(sample_product(in_stock=False, quantity_left=0))
        self.assertIn("Out of stock", block)

    def test_missing_rating_distribution_is_handled_honestly(self):
        block = companion_chat.build_product_block(sample_product(rating_distribution=[], rating_count=0))
        self.assertIn("no rating breakdown provided", block)


class MessageAssemblyTests(unittest.TestCase):
    def test_system_prompt_includes_product_context(self):
        messages = companion_chat.build_messages(
            sample_product(), [ChatMessage(role="user", content="is the battery good?")]
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("iPhone 16", messages[0]["content"])

    def test_without_product_asks_which_one_instead_of_guessing(self):
        messages = companion_chat.build_messages(
            None, [ChatMessage(role="user", content="does it have 8gb ram?")]
        )
        self.assertNotIn("iPhone", messages[0]["content"])
        self.assertIn("not currently viewing", messages[0]["content"])

    def test_conversation_history_preserved_in_order(self):
        history = [
            ChatMessage(role="user", content="battery?"),
            ChatMessage(role="assistant", content="Lasts a full day."),
            ChatMessage(role="user", content="and charging speed?"),
        ]
        messages = companion_chat.build_messages(sample_product(), history)
        self.assertEqual(messages[1]["content"], "battery?")
        self.assertEqual(messages[2]["content"], "Lasts a full day.")
        self.assertEqual(messages[3]["content"], "and charging speed?")

    def test_system_prompt_instructs_balanced_review_sentiment(self):
        messages = companion_chat.build_messages(sample_product(), [ChatMessage(role="user", content="hi")])
        self.assertIn("balanced", messages[0]["content"].lower())

    def test_system_prompt_instructs_not_to_contradict_listed_offers(self):
        messages = companion_chat.build_messages(sample_product(), [ChatMessage(role="user", content="hi")])
        self.assertIn("never contradict", messages[0]["content"].lower())

    def test_system_prompt_instructs_quoting_stats_verbatim(self):
        messages = companion_chat.build_messages(sample_product(), [ChatMessage(role="user", content="hi")])
        content = messages[0]["content"].lower()
        self.assertIn("copy the number", content)
        self.assertIn("do not recompute", content)

    def test_offers_are_rendered_in_context(self):
        messages = companion_chat.build_messages(
            sample_product(offers=["Flat ₹4,000 off on HDFC cards"]),
            [ChatMessage(role="user", content="any bank offers?")],
        )
        self.assertIn("HDFC", messages[0]["content"])


class ComparisonTests(unittest.TestCase):
    def test_comparison_set_lists_every_product(self):
        products = [
            sample_product(title="Phone A", selling_price=50000),
            sample_product(title="Phone B", selling_price=55000),
            sample_product(title="Phone C", selling_price=48000),
        ]
        messages = companion_chat.build_messages(
            None, [ChatMessage(role="user", content="compare these")], comparison_products=products
        )
        content = messages[0]["content"]
        self.assertIn("Phone A", content)
        self.assertIn("Phone B", content)
        self.assertIn("Phone C", content)
        self.assertIn("COMPARISON SET", content)

    def test_no_comparison_block_when_not_comparing(self):
        # "COMPARISON SET" also appears generically in the system prompt's own
        # rule text, so assert on the injected block's specific marker instead.
        messages = companion_chat.build_messages(
            sample_product(), [ChatMessage(role="user", content="hi")], comparison_products=[]
        )
        self.assertNotIn("the shopper has visited all of these this session", messages[0]["content"])

    def test_system_prompt_instructs_neutral_comparison_unless_asked(self):
        messages = companion_chat.build_messages(sample_product(), [ChatMessage(role="user", content="hi")])
        self.assertIn("only state a clear winner", messages[0]["content"].lower())

    def test_comparison_products_can_coexist_with_current_product(self):
        current = sample_product(title="Current Phone")
        others = [sample_product(title="Phone B", selling_price=55000), sample_product(title="Phone C", selling_price=48000)]
        messages = companion_chat.build_messages(
            current, [ChatMessage(role="user", content="compare")], comparison_products=others
        )
        content = messages[0]["content"]
        self.assertIn("PRODUCT: Current Phone", content)
        self.assertIn("Phone B", content)


class SearchHistoryTests(unittest.TestCase):
    def test_search_queries_are_rendered_verbatim(self):
        messages = companion_chat.build_messages(
            sample_product(),
            [ChatMessage(role="user", content="what have I searched for?")],
            search_history=["gaming laptop rtx", "wireless earbuds under 2000"],
        )
        content = messages[0]["content"]
        self.assertIn('"gaming laptop rtx"', content)
        self.assertIn('"wireless earbuds under 2000"', content)
        self.assertIn("SEARCH HISTORY", content)

    def test_no_search_history_block_when_empty(self):
        # "SEARCH HISTORY" also appears generically in the system prompt's own
        # rule text, so assert on the injected block's specific heading instead.
        messages = companion_chat.build_messages(
            sample_product(), [ChatMessage(role="user", content="hi")], search_history=[]
        )
        self.assertNotIn("SEARCH HISTORY (most recent first", messages[0]["content"])

    def test_system_prompt_instructs_accurate_recall_of_searches(self):
        messages = companion_chat.build_messages(sample_product(), [ChatMessage(role="user", content="hi")])
        self.assertIn("list it back accurately", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
