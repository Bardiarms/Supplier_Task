from django import forms
from .models import Questionnaire, Question, Assignment


class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"

            field.widget.attrs["class"] = css_class


class QuestionnaireForm(StyledForm):
    class Meta:
        model = Questionnaire
        fields = ["title", "description"]
        

class QuestionForm(StyledForm):

    option_lines = forms.CharField(
        label="Options (one per line)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Only for Single Choice and Multiple Choice."
    )

    class Meta:
        model = Question
        fields = [
            "text",
            "question_type",
            "order",
            "required",
            "option_lines",
            "show_if_order",
            "show_if_answer"
        ]

    def __init__(self, *args, questionnaire, **kwargs):
        self.questionnaire = questionnaire
        super().__init__(*args, **kwargs)

        self.fields["show_if_order"].help_text = (
            "Order of an earlier question. Leave empty if unconditional."
        )

        self.fields["show_if_answer"].help_text = (
            "Expected answer, e.g. yes or no."
        )

    def clean(self):
        cleaned = super().clean()

        qtype = cleaned.get("question_type")
        order = cleaned.get("order")

        options = [
            line.strip()
            for line in cleaned.get("option_lines", "").splitlines()
            if line.strip()
        ]

        if qtype in ("single", "multiple"):
            if len(options) < 2:
                self.add_error(
                    "option_lines",
                    "Enter at least two options."
                )

            if len(options) != len(set(options)):
                self.add_error(
                    "option_lines",
                    "Options must be unique."
                )

        elif options:
            self.add_error(
                "option_lines",
                "This question type does not need options."
            )

        if order is not None:
            if self.questionnaire.questions.filter(order=order).exists():
                self.add_error(
                    "order",
                    "This order is already used."
                )

        parent_order = cleaned.get("show_if_order")
        expected = cleaned.get("show_if_answer", "").strip()

        if parent_order is None and expected:
            self.add_error(
                "show_if_order",
                "Specify the parent question."
            )

        elif parent_order is not None and not expected:
            self.add_error(
                "show_if_answer",
                "Specify the expected answer."
            )

        elif parent_order is not None and order is not None:

            if parent_order >= order:
                self.add_error(
                    "show_if_order",
                    "The parent must be an earlier question."
                )
            else:
                parent = self.questionnaire.questions.filter(
                    order=parent_order
                ).first()

                if parent is None:
                    self.add_error(
                        "show_if_order",
                        "Parent question not found."
                    )
                elif parent.question_type not in (
                    "yes_no", "single", "multiple"
                ):
                    self.add_error(
                        "show_if_order",
                        "Parent must be a choice question."
                    )
                else:
                    allowed = (
                        ["yes", "no"]
                        if parent.question_type == "yes_no"
                        else [str(x) for x in parent.options]
                    )

                    if expected not in allowed:
                        self.add_error(
                            "show_if_answer",
                            "Answer is not an option of the parent question."
                        )

        cleaned["parsed_options"] = options
        return cleaned
    

class AssignmentForm(StyledForm):

    class Meta:
        model = Assignment
        fields = ["questionnaire", "product"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["questionnaire"].queryset = (
            Questionnaire.objects.filter(
                questions__isnull=False
            ).distinct()
        )

    def clean(self):
        cleaned = super().clean()

        questionnaire = cleaned.get("questionnaire")
        product = cleaned.get("product")

        if questionnaire and product:
            if Assignment.objects.filter(
                questionnaire=questionnaire,
                product=product
            ).exists():
                self.add_error(
                    "product",
                    "This questionnaire has already been sent to this product."
                )

        return cleaned