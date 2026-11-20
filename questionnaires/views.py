from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from .models import Assignment, Questionnaire
from .forms import QuestionnaireForm, QuestionForm, AssignmentForm


def can_manage_questionnaires(user):
    return (
        user.is_superuser
        or user.role == User.Role.ORGANIZATION_MANAGER
    )
    

def is_supplier(user):
    return (
        user.role in [
            User.Role.SUPPLIER_MANAGER,
        ]
        and user.supplier_company_id is not None
    )
    

@login_required
def dashboard(request):

    user = request.user

    if is_supplier(user):

        assignments = Assignment.objects.filter(
            product__supplier_id=user.supplier_company_id
        ).select_related(
            "product", "questionnaire"
        ).order_by("-created_at")

        return render(request, "questionnaires/dashboard.html", {
            "assignments": assignments,
            "manager_view": False
        })

    if user.is_superuser or user.role == User.Role.ORGANIZATION_MANAGER:
        return redirect("manager_dashboard")

    return HttpResponseForbidden("Access denied.")


@login_required
def answer_assignment(request, pk):

    if not is_supplier(request.user):
        return HttpResponseForbidden("Access denied.")

    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        product__supplier_id=request.user.supplier_company_id
    )

    questions = list(assignment.questionnaire.questions.all())
    errors = []

    if request.method == "POST" and not assignment.submitted_at:

        answers = {}
        answers_by_order = {}

        for question in questions:

            # Check conditional visibility
            if question.show_if_order is not None:
                parent_answer = answers_by_order.get(
                    question.show_if_order
                )

                if isinstance(parent_answer, list):
                    visible = question.show_if_answer in parent_answer
                else:
                    visible = parent_answer == question.show_if_answer

                if not visible:
                    continue

            # Read submitted answer
            field = f"question_{question.id}"

            if question.question_type == "multiple":
                value = [
                    v for v in request.POST.getlist(field)
                    if v.strip()
                ]
            else:
                value = request.POST.get(field, "").strip()

            # Required questions
            if not value:
                if question.required:
                    errors.append(f"Answer required: {question.text}")
                continue

            # Validate answer according to its type
            qtype = question.question_type

            if qtype in ("yes_no", "single", "multiple"):

                if qtype == "yes_no":
                    allowed = ["yes", "no"]
                else:
                    allowed = [str(x) for x in question.options]

                if isinstance(value, list):
                    valid = set(value).issubset(set(allowed))
                else:
                    valid = value in allowed

                if not valid:
                    errors.append(f"Invalid choice: {question.text}")
                    continue

            elif qtype == "number":
                try:
                    if not Decimal(value).is_finite():
                        raise InvalidOperation
                except InvalidOperation:
                    errors.append(f"Invalid number: {question.text}")
                    continue

            elif qtype == "date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    errors.append(f"Invalid date: {question.text}")
                    continue

            elif qtype == "rating":
                if value not in ["1", "2", "3", "4", "5"]:
                    errors.append(f"Invalid rating: {question.text}")
                    continue

            elif qtype not in ("text", "long_text"):
                errors.append(f"Unsupported question: {question.text}")
                continue

            answers[str(question.id)] = value
            answers_by_order[question.order] = value

        if not errors:
            assignment.answers = answers
            assignment.submitted_at = timezone.now()
            assignment.answered_by = request.user

            assignment.save(update_fields=[
                "answers", "submitted_at", "answered_by"
            ])

            return redirect("dashboard")

    return render(request, "questionnaires/answer.html", {
        "assignment": assignment,
        "questions": questions,
        "errors": errors
    })
    

@login_required
def manager_dashboard(request):

    if not (
        request.user.is_superuser
        or request.user.role == User.Role.ORGANIZATION_MANAGER
    ):
        return HttpResponseForbidden("Access denied.")

    assignments = list(
        Assignment.objects.select_related(
            "questionnaire",
            "product__supplier"
        ).order_by("-created_at")
    )

    total = len(assignments)

    completed = sum(
        1 for a in assignments if a.submitted_at
    )

    pending = total - completed

    completion_rate = round(
        completed / total * 100, 1
    ) if total else 0

    supplier_stats = {}

    for assignment in assignments:

        supplier = assignment.product.supplier

        if supplier.id not in supplier_stats:
            supplier_stats[supplier.id] = {
                "name": supplier.name,
                "total": 0,
                "completed": 0
            }

        stats = supplier_stats[supplier.id]
        stats["total"] += 1

        if assignment.submitted_at:
            stats["completed"] += 1

    supplier_rows = list(supplier_stats.values())

    for row in supplier_rows:
        row["completion_rate"] = round(
            row["completed"] / row["total"] * 100, 1
        )

    questionnaires = Questionnaire.objects.all()

    return render(request, "questionnaires/manager_dashboard.html", {
        "assignments": assignments,
        "questionnaires": questionnaires,
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "supplier_rows": supplier_rows
    })
    
@login_required
def questionnaire_results(request, pk):

    if not (
        request.user.is_superuser
        or request.user.role == User.Role.ORGANIZATION_MANAGER
    ):
        return HttpResponseForbidden("Access denied.")

    questionnaire = get_object_or_404(Questionnaire, pk=pk)

    questions = list(questionnaire.questions.all())

    assignments = list(
        Assignment.objects.filter(
            questionnaire=questionnaire,
            submitted_at__isnull=False
        ).select_related(
            "product__supplier",
            "answered_by"
        )
    )

    analysis = []

    for question in questions:

        values = []

        for assignment in assignments:
            value = assignment.answers.get(str(question.id))

            if value not in (None, "", []):
                values.append(value)

        result = {
            "text": question.text,
            "type": question.question_type,
            "count": len(values),
            "options": [],
            "examples": [],
            "average": ""
        }

        qtype = question.question_type

        if qtype in ("yes_no", "single", "multiple", "rating"):

            if qtype == "yes_no":
                options = ["yes", "no"]
            elif qtype == "rating":
                options = ["1", "2", "3", "4", "5"]
            else:
                options = [str(x) for x in question.options]

            for option in options:

                count = sum(
                    1
                    for value in values
                    if (
                        option in value
                        if isinstance(value, list)
                        else str(value) == option
                    )
                )

                percentage = round(
                    count / len(values) * 100, 1
                ) if values else 0

                result["options"].append({
                    "label": option,
                    "count": count,
                    "percentage": percentage
                })

            if qtype == "rating" and values:
                result["average"] = str(round(
                    sum(int(v) for v in values) / len(values), 2
                ))

        elif qtype == "number":

            numbers = []

            for value in values:
                try:
                    numbers.append(Decimal(str(value)))
                except (InvalidOperation, TypeError, ValueError):
                    continue

            if numbers:
                result["average"] = str(round(
                    sum(numbers) / len(numbers), 2
                ))

        else:
            result["examples"] = [str(v) for v in values[:5]]

        analysis.append(result)

    submissions = []

    for assignment in assignments:
        details = []

        for question in questions:
            value = assignment.answers.get(str(question.id))

            if value in (None, "", []):
                continue

            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)

            details.append({
                "question": question.text,
                "answer": str(value)
            })

        submissions.append({
            "supplier": assignment.product.supplier.name,
            "product": assignment.product.name,
            "answered_by": assignment.answered_by,
            "submitted_at": assignment.submitted_at,
            "details": details
        })

    return render(request, "questionnaires/results.html", {
        "questionnaire": questionnaire,
        "analysis": analysis,
        "submissions": submissions
    })
    
    
@login_required
def create_questionnaire(request):

    if not can_manage_questionnaires(request.user):
        return HttpResponseForbidden("Access denied.")

    form = QuestionnaireForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        questionnaire = form.save(commit=False)
        questionnaire.created_by = request.user
        questionnaire.save()

        return redirect(
            "questionnaire_questions",
            pk=questionnaire.id
        )

    return render(request, "questionnaires/form_page.html", {
        "form": form,
        "title": "Create Questionnaire",
        "submit_label": "Create and Add Questions"
    })
    

@login_required
def add_question(request, pk):

    if not can_manage_questionnaires(request.user):
        return HttpResponseForbidden("Access denied.")

    questionnaire = get_object_or_404(
        Questionnaire,
        pk=pk
    )

    locked = questionnaire.assignments.exists()

    if request.method == "POST" and locked:
        return HttpResponseForbidden(
            "Cannot modify an assigned questionnaire."
        )

    form = None

    if not locked:
        form = QuestionForm(
            request.POST or None,
            questionnaire=questionnaire
        )

        if request.method == "POST" and form.is_valid():

            question = form.save(commit=False)
            question.questionnaire = questionnaire
            question.options = form.cleaned_data["parsed_options"]
            question.save()

            return redirect(
                "questionnaire_questions",
                pk=questionnaire.id
            )

    return render(request, "questionnaires/question_form.html", {
        "questionnaire": questionnaire,
        "questions": questionnaire.questions.all(),
        "form": form,
        "locked": locked
    })
    

@login_required
def create_assignment(request):

    if not can_manage_questionnaires(request.user):
        return HttpResponseForbidden("Access denied.")

    form = AssignmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        assignment = form.save(commit=False)
        assignment.assigned_by = request.user
        assignment.save()

        return redirect("manager_dashboard")

    return render(request, "questionnaires/form_page.html", {
        "form": form,
        "title": "Send Questionnaire",
        "submit_label": "Send to Supplier"
    })