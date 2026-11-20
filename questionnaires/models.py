from django.db import models
from django.conf import settings



class Questionnaire(models.Model):

    title = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_questionnaires"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
class Question(models.Model):

    class Type(models.TextChoices):
        YES_NO = "yes_no", "Yes / No"
        SINGLE = "single", "Single Choice"
        MULTIPLE = "multiple", "Multiple Choice"
        TEXT = "text", "Short Text"
        LONG_TEXT = "long_text", "Long Text"
        NUMBER = "number", "Number"
        DATE = "date", "Date"
        RATING = "rating", "Rating (1-5)"

    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    text = models.TextField()

    question_type = models.CharField(
        max_length=20,
        choices=Type.choices
    )

    order = models.PositiveIntegerField()
    required = models.BooleanField(default=True)

    options = models.JSONField(
        default=list,
        blank=True
    )

    show_if_order = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    show_if_answer = models.CharField(
        max_length=100,
        blank=True
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["questionnaire", "order"],
                name="unique_question_order"
            )
        ]

    def __str__(self):
        return self.text
    

class Assignment(models.Model):

    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.PROTECT,
        related_name="assignments"
    )

    product = models.ForeignKey(
        "suppliers.Product",
        on_delete=models.PROTECT,
        related_name="assignments"
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["questionnaire", "product"],
                name="unique_questionnaire_product_assignment"
            )
        ]

    def __str__(self):
        return f"{self.questionnaire.title} - {self.product.name}"
    
    answers = models.JSONField(
        default=dict,
        blank=True
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="answered_assignments"
    )