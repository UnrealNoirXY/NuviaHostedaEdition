"""Test della fonte di verità unica per l'accesso alle recensioni (reviews/access.py)."""

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from clients.models import Company
from resort.models import Resort
from reviews.models import Review, ReviewSource
from reviews.access import can_access_reviews, scope_reviews


class ReviewAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = Company.objects.create(name="Company A")
        cls.company_b = Company.objects.create(name="Company B")
        cls.resort_a = Resort.objects.create(name="Resort A", company=cls.company_a)
        cls.resort_b = Resort.objects.create(name="Resort B", company=cls.company_b)
        cls.source = ReviewSource.objects.create(
            name="Src", scraper_identifier="test/acc"
        )
        cls.rev_a = Review.objects.create(
            resort=cls.resort_a, source=cls.source, rating=5, title="A",
            review_date=timezone.now(), review_id="acc_a",
        )
        cls.rev_b = Review.objects.create(
            resort=cls.resort_b, source=cls.source, rating=1, title="B",
            review_date=timezone.now(), review_id="acc_b",
        )

        cls.superuser = User.objects.create_user(
            "su_acc", "su_acc@t.com", "pw", role=User.SUPERADMIN, is_superuser=True
        )
        cls.owner_a = User.objects.create_user(
            "own_acc", "own_acc@t.com", "pw", role=User.OWNER, company=cls.company_a
        )
        cls.director_a = User.objects.create_user(
            "dir_acc", "dir_acc@t.com", "pw", role=User.DIRECTOR, resort=cls.resort_a
        )
        cls.receptionist = User.objects.create_user(
            "rec_acc", "rec_acc@t.com", "pw", role=User.RECEPTIONIST
        )

    # ---- can_access_reviews ----
    def test_gate_allows_roles_and_superuser(self):
        self.assertTrue(can_access_reviews(self.superuser))
        self.assertTrue(can_access_reviews(self.owner_a))
        self.assertTrue(can_access_reviews(self.director_a))

    def test_gate_denies_unlisted_role(self):
        self.assertFalse(can_access_reviews(self.receptionist))

    # ---- scope_reviews ----
    def test_superuser_sees_all(self):
        self.assertEqual(scope_reviews(Review.objects.all(), self.superuser).count(), 2)

    def test_company_role_sees_only_own_company(self):
        qs = scope_reviews(Review.objects.all(), self.owner_a)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.rev_a)

    def test_director_sees_only_own_resort(self):
        qs = scope_reviews(Review.objects.all(), self.director_a)
        self.assertEqual(list(qs), [self.rev_a])

    def test_unlisted_role_sees_nothing_no_leak(self):
        # Mai un fallback "tutte": un ruolo non previsto non deve vedere recensioni altrui.
        self.assertEqual(scope_reviews(Review.objects.all(), self.receptionist).count(), 0)

    def test_company_role_without_company_sees_nothing(self):
        orphan = User.objects.create_user(
            "orph", "orph@t.com", "pw", role=User.OWNER, company=None
        )
        self.assertEqual(scope_reviews(Review.objects.all(), orphan).count(), 0)
