import datetime
from urllib.request import urlopen

from django.test import LiveServerTestCase, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import resolve, reverse
from django.utils import timezone

from .models import Animal, Choice, Question


def create_question(question_text, days):
    # Helper: negative days means past, positive days means future.
    pub_date = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=pub_date)


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_old_question(self):
        # Older than 24 hours should be reported as not recent.
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        # Within the last 24 hours should be reported as recent.
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


class QuestionIndexViewTests(TestCase):
    def _get_index(self):
        # Small helper so index-page requests are consistent across tests.
        return self.client.get(reverse("polls:index"))

    def _assert_index_questions(self, expected_questions):
        response = self._get_index()
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["latest_question_list"], expected_questions)
        return response

    def test_no_questions(self):
        # With no data, the page should show the empty-state message.
        response = self._assert_index_questions([])
        self.assertContains(response, "No polls are available.")

    def test_past_question(self):
        # Questions from the past should appear in the list.
        question = create_question("Past question.", -30)
        self._assert_index_questions([question])

    def test_future_question(self):
        # Questions scheduled in the future should not be shown yet.
        create_question("Future question.", 30)
        response = self._assert_index_questions([])
        self.assertContains(response, "No polls are available.")

    def test_future_question_and_past_question(self):
        # If both exist, only already-published questions should be visible.
        question = create_question("Past question.", -30)
        create_question("Future question.", 30)
        self._assert_index_questions([question])

    def test_two_past_questions(self):
        # Multiple past questions should be sorted newest first.
        question1 = create_question("Past question 1.", -30)
        question2 = create_question("Past question 2.", -5)
        self._assert_index_questions([question2, question1])


class QuestionDetailViewTests(TestCase):
    def _get_detail(self, question):
        return self.client.get(reverse("polls:detail", args=(question.id,)))

    def test_future_question(self):
        future_question = create_question("Future question.", 5)
        response = self._get_detail(future_question)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        # A published question should render its detail page content.
        past_question = create_question("Past Question.", -5)
        response = self._get_detail(past_question)
        self.assertContains(response, past_question.question_text)


class AnimalTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lion = Animal.objects.create(name="lion", sound="roar")
        cls.cat = Animal.objects.create(name="cat", sound="meow")

    def test_animals_can_speak(self):
        # Checks that the model method returns the expected formatted sentence.
        self.assertEqual(self.lion.speak(), 'The lion says "roar"')
        self.assertEqual(self.cat.speak(), 'The cat says "meow"')


class PollsURLSimpleTests(SimpleTestCase):
    # SimpleTestCase: no database access, just URL wiring checks.
    def test_index_url_resolves_to_named_view(self):
        url = reverse("polls:index")
        match = resolve(url)
        self.assertEqual(match.view_name, "polls:index")


class VoteTransactionTests(TransactionTestCase):
    def test_vote_view_increments_vote_count(self):
        question = create_question("Transactional vote test.", -1)
        choice = Choice.objects.create(question=question, choice_text="Yes", votes=0)

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)),
            {"choice": choice.id},
        )

        choice.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(choice.votes, 1)


class PollsLiveServerTests(LiveServerTestCase):
    def test_live_server_serves_index_page(self):
        response = urlopen(f"{self.live_server_url}{reverse('polls:index')}")
        body = response.read().decode("utf-8")
        self.assertEqual(response.getcode(), 200)
        self.assertIn("No polls are available.", body)
        